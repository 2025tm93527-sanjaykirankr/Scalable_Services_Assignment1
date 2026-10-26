import requests, uuid, sys

base="http://127.0.0.1:8000"
key=f"e2e-{uuid.uuid4()}"
r=requests.post(f"{base}/api/v1/bookings",headers={"Idempotency-Key":key},
                json={"customer_id":"e2e-customer","slot_id":"slot-1","amount":12.5},timeout=20)
print("Create booking:",r.status_code,r.text)
if r.status_code != 201:
    sys.exit("FAIL: booking was not confirmed")
booking=r.json()
g=requests.get(f"{base}/api/v1/bookings/{booking['booking_id']}",timeout=5)
print("Read booking:",g.status_code,g.text)
sys.exit(0 if g.status_code==200 and g.json()["status"]=="CONFIRMED" else 1)
