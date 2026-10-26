import concurrent.futures, uuid, requests, time

BASE="http://127.0.0.1:8000/api/v1/bookings"
N=20
def send(i):
    key=f"concurrency-{uuid.uuid4()}"
    try:
        r=requests.post(BASE,headers={"Idempotency-Key":key},
            json={"customer_id":f"load-user-{i}","slot_id":"slot-2","amount":10.0},timeout=20)
        return r.status_code, r.text
    except Exception as exc:
        return 0,str(exc)

if __name__=="__main__":
    print(f"Sending {N} parallel requests for slot-2 (capacity 1).")
    with concurrent.futures.ThreadPoolExecutor(max_workers=N) as pool:
        results=list(pool.map(send,range(N)))
    success=sum(1 for status,_ in results if status==201)
    rejected=sum(1 for status,_ in results if status==409)
    other=[item for item in results if item[0] not in (201,409)]
    print(f"HTTP 201 successes: {success}")
    print(f"HTTP 409 rejections: {rejected}")
    if other: print("Unexpected responses:",other)
    print("PASS" if success==1 and rejected==N-1 and not other else "CHECK RESULTS")
    for status,body in results:
        print(status,body[:180])
