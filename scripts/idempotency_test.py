import requests, uuid, json

URL="http://127.0.0.1:8000/api/v1/bookings"
key=f"idempotency-demo-{uuid.uuid4()}"
payload={"customer_id":"demo-customer","slot_id":"slot-1","amount":19.5}

def post(data):
    return requests.post(URL,headers={"Idempotency-Key":key},json=data,timeout=20)

first=post(payload)
replay=post(payload)
changed=post({**payload,"amount":20.0})
print("First call:",first.status_code,first.text)
print("Exact replay:",replay.status_code,replay.text)
print("Changed payload:",changed.status_code,changed.text)
same=(first.status_code==replay.status_code and first.json()==replay.json())
conflict=changed.status_code==409
print("PASS" if same and conflict else "CHECK RESULTS")
