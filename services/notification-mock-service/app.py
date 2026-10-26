import os, sqlite3, uuid
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from common import request_id, log_event

DB=os.getenv("NOTIFICATION_DB","notification.db")
app=FastAPI(title="Notification Mock Service",version="1.0.0",
            description="Records simulated notifications; no email or SMS is sent.")

def connect():
    con=sqlite3.connect(DB,timeout=15)
    con.row_factory=sqlite3.Row
    return con

with connect() as con:
    con.execute("""CREATE TABLE IF NOT EXISTS notifications(
      notification_id TEXT PRIMARY KEY, booking_id TEXT UNIQUE NOT NULL,
      customer_id TEXT NOT NULL, message TEXT NOT NULL)""")

class NotificationInput(BaseModel):
    booking_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    message: str = Field(min_length=1)

@app.get("/health")
def health():
    return {"status":"ok","service":"notification-mock-service"}

@app.post("/api/v1/notifications")
def notify(body: NotificationInput, request: Request):
    rid=request_id(request)
    with connect() as con:
        con.execute("INSERT OR IGNORE INTO notifications VALUES(?,?,?,?)",
                    (str(uuid.uuid4()),body.booking_id,body.customer_id,body.message))
        row=con.execute("SELECT * FROM notifications WHERE booking_id=?",(body.booking_id,)).fetchone()
    log_event("notification_recorded",rid,booking_id=body.booking_id)
    return {"notification_id":row["notification_id"],"booking_id":row["booking_id"],"status":"RECORDED"}
