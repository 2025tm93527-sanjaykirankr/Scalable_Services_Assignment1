import os, sqlite3, uuid
from contextlib import closing
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from common import request_id, log_event, error_response

DB = os.getenv("INVENTORY_DB", "inventory.db")
app = FastAPI(title="Inventory Service", version="1.0.0",
              description="Owns appointment slot capacity and reservations.")

def connect():
    con = sqlite3.connect(DB, timeout=15, isolation_level=None)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with closing(connect()) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS slots (
            slot_id TEXT PRIMARY KEY, capacity INTEGER NOT NULL,
            remaining INTEGER NOT NULL CHECK(remaining >= 0))""")
        con.execute("""CREATE TABLE IF NOT EXISTS reservations (
            reservation_id TEXT PRIMARY KEY, slot_id TEXT NOT NULL,
            booking_id TEXT NOT NULL UNIQUE, status TEXT NOT NULL)""")
        con.execute("INSERT OR IGNORE INTO slots(slot_id, capacity, remaining) VALUES ('slot-1',5,5)")
        con.execute("INSERT OR IGNORE INTO slots(slot_id, capacity, remaining) VALUES ('slot-2',1,1)")
init_db()

class ReserveInput(BaseModel):
    booking_id: str = Field(min_length=1, max_length=100)

class ReleaseInput(BaseModel):
    booking_id: str = Field(min_length=1, max_length=100)

@app.get("/health")
def health():
    return {"status":"ok","service":"inventory-service"}

@app.get("/api/v1/slots")
def list_slots():
    with closing(connect()) as con:
        rows = con.execute("SELECT slot_id, capacity, remaining FROM slots ORDER BY slot_id").fetchall()
    return {"slots":[dict(row) for row in rows]}

@app.post("/api/v1/slots/{slot_id}/reserve")
def reserve(slot_id: str, body: ReserveInput, request: Request):
    rid = request_id(request)
    con = connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        existing = con.execute("SELECT * FROM reservations WHERE booking_id=?", (body.booking_id,)).fetchone()
        if existing:
            con.commit()
            return {"reservation_id":existing["reservation_id"],"booking_id":body.booking_id,
                    "slot_id":existing["slot_id"],"status":existing["status"],"replayed":True}
        updated = con.execute(
            "UPDATE slots SET remaining=remaining-1 WHERE slot_id=? AND remaining>0", (slot_id,)
        ).rowcount
        if updated != 1:
            slot = con.execute("SELECT slot_id FROM slots WHERE slot_id=?", (slot_id,)).fetchone()
            con.rollback()
            if not slot:
                return error_response(404,"SLOT_NOT_FOUND","Appointment slot does not exist",rid)
            return error_response(409,"SLOT_FULL","No capacity remains for this slot",rid)
        reservation_id = str(uuid.uuid4())
        con.execute("INSERT INTO reservations(reservation_id,slot_id,booking_id,status) VALUES(?,?,?,'RESERVED')",
                    (reservation_id,slot_id,body.booking_id))
        con.commit()
        log_event("slot_reserved",rid,slot_id=slot_id,booking_id=body.booking_id)
        return {"reservation_id":reservation_id,"booking_id":body.booking_id,
                "slot_id":slot_id,"status":"RESERVED","replayed":False}
    except sqlite3.IntegrityError:
        con.rollback()
        row = con.execute("SELECT * FROM reservations WHERE booking_id=?", (body.booking_id,)).fetchone()
        if row:
            return {"reservation_id":row["reservation_id"],"booking_id":body.booking_id,
                    "slot_id":row["slot_id"],"status":row["status"],"replayed":True}
        return error_response(409,"RESERVATION_CONFLICT","Reservation conflicts with existing data",rid)
    finally:
        con.close()

@app.post("/api/v1/slots/{slot_id}/release")
def release(slot_id: str, body: ReleaseInput, request: Request):
    rid = request_id(request)
    with closing(connect()) as con:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT * FROM reservations WHERE booking_id=?", (body.booking_id,)).fetchone()
        if not row:
            con.commit()
            return {"released":False,"reason":"reservation_not_found"}
        if row["status"] == "RELEASED":
            con.commit()
            return {"released":False,"reason":"already_released"}
        con.execute("UPDATE reservations SET status='RELEASED' WHERE booking_id=?", (body.booking_id,))
        con.execute("UPDATE slots SET remaining=MIN(capacity,remaining+1) WHERE slot_id=?", (row["slot_id"],))
        con.commit()
    log_event("slot_released",rid,slot_id=row["slot_id"],booking_id=body.booking_id)
    return {"released":True,"booking_id":body.booking_id,"slot_id":row["slot_id"]}
