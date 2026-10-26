import os, sqlite3, uuid, json, hashlib, time, random
from contextlib import closing
import requests
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from common import request_id, log_event, error_response

DB=os.getenv("BOOKING_DB","booking.db")
INVENTORY_URL=os.getenv("INVENTORY_URL","http://127.0.0.1:8001").rstrip("/")
PAYMENT_URL=os.getenv("PAYMENT_URL","http://127.0.0.1:8002").rstrip("/")
NOTIFICATION_URL=os.getenv("NOTIFICATION_URL","http://127.0.0.1:8003").rstrip("/")
app=FastAPI(title="Booking Service",version="1.0.0",
            description="Orchestrates appointment booking across inventory, mock payment, and notification services.")

def connect():
    con=sqlite3.connect(DB,timeout=30,isolation_level=None)
    con.row_factory=sqlite3.Row
    return con

with closing(connect()) as con:
    con.execute("""CREATE TABLE IF NOT EXISTS bookings(
      booking_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, slot_id TEXT NOT NULL,
      amount REAL NOT NULL, status TEXT NOT NULL, payment_id TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    con.execute("""CREATE TABLE IF NOT EXISTS idempotency(
      idem_key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, status_code INTEGER NOT NULL,
      response_json TEXT NOT NULL)""")

class BookingInput(BaseModel):
    customer_id: str = Field(min_length=1, max_length=100)
    slot_id: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0, le=100000)

def downstream(method, url, rid, payload=None, timeout=1.5):
    headers={"X-Request-ID":rid}
    return requests.request(method,url,json=payload,headers=headers,timeout=timeout)

def payment_with_retry(booking_id, amount, rid):
    payload={"booking_id":booking_id,"amount":amount,"idempotency_key":f"charge:{booking_id}"}
    last_error=None
    for attempt in range(3):
        try:
            response=downstream("POST",f"{PAYMENT_URL}/api/v1/payments/charge",rid,payload,timeout=1.0)
            if response.status_code < 500:
                return response
            last_error=f"payment service returned HTTP {response.status_code}"
        except requests.RequestException as exc:
            last_error=str(exc)
        if attempt < 2:
            delay=(0.15*(2**attempt))+random.uniform(0,0.08)
            log_event("payment_retry",rid,attempt=attempt+1,delay_seconds=round(delay,3))
            time.sleep(delay)
    raise RuntimeError(last_error or "payment service unavailable")

@app.get("/health")
def health():
    return {"status":"ok","service":"booking-service"}

@app.post("/api/v1/bookings")
def create_booking(body: BookingInput, request: Request,
                   idempotency_key: str | None = Header(default=None, alias="Idempotency-Key",
                                                        description="Unique key used to safely replay this booking request")):
    rid=request_id(request)
    key=idempotency_key
    if not key:
        return error_response(400,"IDEMPOTENCY_KEY_REQUIRED","Idempotency-Key header is required",rid)
    payload=body.model_dump()
    fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    con=connect()
    try:
        # Serializes concurrent requests using the same SQLite database. Suitable for this demo,
        # not a high-throughput production workflow.
        con.execute("BEGIN IMMEDIATE")
        previous=con.execute("SELECT * FROM idempotency WHERE idem_key=?",(key,)).fetchone()
        if previous:
            if previous["fingerprint"] != fingerprint:
                con.rollback()
                return error_response(409,"IDEMPOTENCY_CONFLICT","Key was already used with a different request body",rid)
            con.commit()
            log_event("idempotency_replay",rid,idempotency_key=key)
            return JSONResponse(status_code=previous["status_code"],content=json.loads(previous["response_json"]),
                                headers={"X-Request-ID":rid,"Idempotency-Replayed":"true"})

        booking_id=str(uuid.uuid4())
        try:
            inv=downstream("POST",f"{INVENTORY_URL}/api/v1/slots/{body.slot_id}/reserve",rid,
                           {"booking_id":booking_id},timeout=2.0)
            if inv.status_code >= 400:
                data=inv.json()
                status=inv.status_code
                content=data
                con.execute("INSERT INTO idempotency VALUES(?,?,?,?)",
                            (key,fingerprint,status,json.dumps(content)))
                con.commit()
                return JSONResponse(status_code=status,content=content,headers={"X-Request-ID":rid})
            reservation=inv.json()
        except requests.RequestException as exc:
            con.rollback()
            return error_response(503,"INVENTORY_UNAVAILABLE",f"Inventory service unavailable: {exc}",rid)

        try:
            pay=payment_with_retry(booking_id,body.amount,rid)
            if pay.status_code >= 400:
                raise RuntimeError(f"payment returned HTTP {pay.status_code}: {pay.text}")
            payment=pay.json()
        except Exception as exc:
            try:
                downstream("POST",f"{INVENTORY_URL}/api/v1/slots/{body.slot_id}/release",rid,
                           {"booking_id":booking_id},timeout=2.0)
            except requests.RequestException:
                log_event("compensation_failed",rid,booking_id=booking_id)
            content={"error":{"code":"PAYMENT_FAILED","message":"Payment failed after bounded retries; reservation compensation was attempted",
                              "request_id":rid}}
            con.execute("INSERT INTO bookings(booking_id,customer_id,slot_id,amount,status) VALUES(?,?,?,?,?)",
                        (booking_id,body.customer_id,body.slot_id,body.amount,"FAILED"))
            con.execute("INSERT INTO idempotency VALUES(?,?,503,?)",(key,fingerprint,json.dumps(content)))
            con.commit()
            log_event("booking_failed",rid,booking_id=booking_id,reason=str(exc))
            return JSONResponse(status_code=503,content=content,headers={"X-Request-ID":rid})

        con.execute("INSERT INTO bookings(booking_id,customer_id,slot_id,amount,status,payment_id) VALUES(?,?,?,?,?,?)",
                    (booking_id,body.customer_id,body.slot_id,body.amount,"CONFIRMED",payment["payment_id"]))
        response={"booking_id":booking_id,"customer_id":body.customer_id,"slot_id":body.slot_id,
                  "amount":body.amount,"status":"CONFIRMED","reservation_id":reservation["reservation_id"],
                  "payment_id":payment["payment_id"],"notification_status":"PENDING"}
        try:
            notification=downstream("POST",f"{NOTIFICATION_URL}/api/v1/notifications",rid,
                {"booking_id":booking_id,"customer_id":body.customer_id,
                 "message":f"Appointment booking {booking_id} confirmed"},timeout=1.5)
            if notification.status_code < 400:
                response["notification_status"]="RECORDED"
        except requests.RequestException:
            log_event("notification_unavailable",rid,booking_id=booking_id)
        con.execute("INSERT INTO idempotency VALUES(?,?,201,?)",(key,fingerprint,json.dumps(response)))
        con.commit()
        log_event("booking_confirmed",rid,booking_id=booking_id,slot_id=body.slot_id)
        return JSONResponse(status_code=201,content=response,headers={"X-Request-ID":rid})
    except sqlite3.Error as exc:
        con.rollback()
        log_event("database_error",rid,error=str(exc))
        return error_response(500,"DATABASE_ERROR","Booking persistence failed",rid)
    finally:
        con.close()

@app.get("/api/v1/bookings/{booking_id}")
def get_booking(booking_id: str, request: Request):
    rid=request_id(request)
    with closing(connect()) as con:
        row=con.execute("SELECT * FROM bookings WHERE booking_id=?",(booking_id,)).fetchone()
    if not row:
        return error_response(404,"BOOKING_NOT_FOUND","Booking does not exist",rid)
    return dict(row)
