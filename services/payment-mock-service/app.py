import os, sqlite3, hashlib, json, uuid
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from common import request_id, log_event, error_response

DB = os.getenv("PAYMENT_DB","payment.db")
MODE = os.getenv("PAYMENT_MODE","success").lower()
app = FastAPI(title="Payment Mock Service", version="1.0.0",
              description="Mock payment provider; never contacts a real gateway.")

def connect():
    con=sqlite3.connect(DB,timeout=15,isolation_level=None)
    con.row_factory=sqlite3.Row
    return con

with connect() as con:
    con.execute("""CREATE TABLE IF NOT EXISTS payments(
      payment_id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL,
      fingerprint TEXT NOT NULL, booking_id TEXT NOT NULL, amount REAL NOT NULL,
      status TEXT NOT NULL)""")

class ChargeInput(BaseModel):
    booking_id: str = Field(min_length=1)
    amount: float = Field(gt=0)
    idempotency_key: str = Field(min_length=1)

@app.get("/health")
def health():
    return {"status":"ok","service":"payment-mock-service","mode":MODE}

@app.post("/api/v1/payments/charge")
def charge(body: ChargeInput, request: Request):
    rid=request_id(request)
    fingerprint=hashlib.sha256(json.dumps({"booking_id":body.booking_id,"amount":body.amount},
                                          sort_keys=True).encode()).hexdigest()
    con=connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        old=con.execute("SELECT * FROM payments WHERE idempotency_key=?",(body.idempotency_key,)).fetchone()
        if old:
            if old["fingerprint"] != fingerprint:
                con.rollback()
                return error_response(409,"IDEMPOTENCY_CONFLICT","Payment key reused with a different payload",rid)
            con.commit()
            return {"payment_id":old["payment_id"],"booking_id":old["booking_id"],
                    "amount":old["amount"],"status":old["status"],"replayed":True}
        if MODE == "fail":
            con.rollback()
            return error_response(503,"PAYMENT_DECLINED","Mock payment service configured to fail",rid)
        payment_id=str(uuid.uuid4())
        con.execute("INSERT INTO payments VALUES(?,?,?,?,?,'CHARGED')",
                    (payment_id,body.idempotency_key,fingerprint,body.booking_id,body.amount))
        con.commit()
        log_event("payment_charged",rid,booking_id=body.booking_id,payment_id=payment_id)
        return {"payment_id":payment_id,"booking_id":body.booking_id,
                "amount":body.amount,"status":"CHARGED","replayed":False}
    finally:
        con.close()
