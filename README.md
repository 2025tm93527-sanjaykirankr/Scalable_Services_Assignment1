# Scalable Services — Assignment 1
## Appointment Booking Microservices (Python / FastAPI / SQLite)

This project is a runnable educational implementation aligned to the assignment brief: four independently runnable services, separate SQLite databases, REST-only service communication, a cross-service booking transaction, concurrency protection, idempotency, and a mock downstream dependency. The selected optional challenge is **3A: Resilience** (bounded retries with exponential backoff/jitter and graceful failure).

> Important: This is a working reference implementation for learning and adaptation. Run it, inspect it, capture your own terminal/API evidence, and make sure every team member can explain it. The assignment requires a PDF report, evidence, demo video, contribution/reflection, and an AI-use declaration; those cannot be truthfully completed without your own execution and team details.

## Domain and services

- **booking-service** (port 8000): accepts a booking request, orchestrates the transaction, stores booking/idempotency records.
- **inventory-service** (port 8001): owns appointment-slot capacity and atomically reserves/releases capacity.
- **payment-mock-service** (port 8002): simulated payment dependency; idempotent charge operation; can be configured to fail for resilience demos.
- **notification-mock-service** (port 8003): stores simulated booking notifications.

Each service has its own folder, requirements file, SQLite database, `/health`, `/openapi.json`, and `/docs`. No service reads another service's database. All service URLs and ports are configurable through environment variables.

## Requirements

- Python 3.10+
- pip

## Run locally

Open four terminals from this directory. In each terminal, create a virtual environment (optional but recommended), install dependencies, and start the indicated service.

### Terminal 1 — inventory

```bash
cd services/inventory-service
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8001
```

### Terminal 2 — payment mock

```bash
cd services/payment-mock-service
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8002
```

### Terminal 3 — notification mock

```bash
cd services/notification-mock-service
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8003
```

### Terminal 4 — booking orchestrator

```bash
cd services/booking-service
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

Each service creates its own SQLite database in its own directory. To reset demo data, stop the service and delete that service's `*.db` file. Inventory seeds two slots on first run: `slot-1` with capacity 5 and `slot-2` with capacity 1.

## Main flow demo

Create a booking (the `Idempotency-Key` is required):

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/bookings ^
  -H "Content-Type: application/json" ^
  -H "Idempotency-Key: demo-001" ^
  -d "{\"customer_id\":\"cust-1\",\"slot_id\":\"slot-1\",\"amount\":25.00}"
```

On macOS/Linux use `\` at the end of lines, or send the same JSON as one line:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/bookings -H "Content-Type: application/json" -H "Idempotency-Key: demo-001" -d '{"customer_id":"cust-1","slot_id":"slot-1","amount":25.00}'
```

Repeat the exact request with the same key. The same stored response should be returned and no second booking/payment should be created. Reuse the key with a different payload to receive HTTP 409.

Inspect APIs:
- Booking: http://127.0.0.1:8000/docs
- Inventory: http://127.0.0.1:8001/docs
- Payment mock: http://127.0.0.1:8002/docs
- Notification mock: http://127.0.0.1:8003/docs

## Challenge 1 — concurrency

From the project root, with all services running:

```bash
pip install -r scripts/requirements.txt
python scripts/concurrency_test.py
```

The script sends 20 concurrent requests to `slot-2`, which has capacity 1. Exactly one should succeed; the rest should be rejected. Use a fresh idempotency key per request. If you have already used `slot-2`, reset the inventory DB while the service is stopped.

Why check-then-update is unsafe: multiple requests can all read the same remaining capacity before any writes, then all decrement it. Inventory uses a single atomic conditional SQL update (`remaining > 0`) so only one competing request can decrement the last unit.

## Challenge 2 — idempotency

```bash
python scripts/idempotency_test.py
```

This script checks first request vs exact replay, then verifies that the same key with a changed payload is rejected. The booking service uses a unique idempotency key, a canonical JSON fingerprint, and a SQLite `BEGIN IMMEDIATE` transaction to serialize concurrent duplicate-key requests. Payment mock also uses a unique idempotency key per booking.

## Challenge 3A — resilience demo

1. Start all four services and make a successful booking.
2. Stop payment-mock-service.
3. Send a booking with a new key. Booking makes bounded retries with exponential backoff and jitter, then gracefully fails and asks inventory to release the reservation.
4. Restart payment mock and retry with a new idempotency key.

The retry policy is intentionally bounded for a quick classroom demo. It does not replace production-grade timeouts, circuit breakers, distributed tracing, or a durable saga/outbox.

## Environment variables

| Service | Variable | Default |
|---|---|---|
| booking | `BOOKING_DB` | `booking.db` |
| booking | `INVENTORY_URL` | `http://127.0.0.1:8001` |
| booking | `PAYMENT_URL` | `http://127.0.0.1:8002` |
| booking | `NOTIFICATION_URL` | `http://127.0.0.1:8003` |
| inventory | `INVENTORY_DB` | `inventory.db` |
| payment mock | `PAYMENT_DB` | `payment.db` |
| payment mock | `PAYMENT_MODE` | `success` (`fail` returns a simulated failure) |
| notification mock | `NOTIFICATION_DB` | `notification.db` |

All services accept an optional `X-Request-ID` header. A generated or forwarded request ID is returned in the response and included in structured JSON logs.

## Business rules (BR) and traceability

- **BR1:** A slot cannot be overbooked. Implemented by inventory's atomic conditional update; exercise with `scripts/concurrency_test.py`.
- **BR2:** A booking request requires a customer ID, slot ID, positive amount, and `Idempotency-Key`. Enforced by request validation and endpoint checks.
- **BR3:** Reusing an idempotency key with the same payload returns the original response; a changed payload returns 409. Exercise with `scripts/idempotency_test.py`.
- **BR4:** Payment failure must not leave the slot reserved. Booking calls inventory release after failed payment; demonstrate with payment mock stopped or `PAYMENT_MODE=fail`.
- **BR5:** A booking notification is attempted only after payment succeeds.

Run the business-rule tests from the project root after installing `tests/requirements.txt` and the booking and inventory service dependencies:

```bash
python -m unittest discover -s tests -p test_business_rules.py -v
```

The tests cover BR1–BR5. Recorded test and end-to-end output is in `evidence/tests/`.

## API summary

- `POST /api/v1/bookings` — create or replay a booking; requires `Idempotency-Key`.
- `GET /api/v1/bookings/{booking_id}` — retrieve a booking.
- `GET /api/v1/slots` — list inventory slots.
- `POST /api/v1/slots/{slot_id}/reserve` — atomically reserve one unit.
- `POST /api/v1/slots/{slot_id}/release` — release one unit after a failed booking.
- `POST /api/v1/payments/charge` — mock idempotent charge.
- `POST /api/v1/notifications` — record a mock notification.
- `GET /health` — service health.

Errors use a consistent JSON shape: `{"error":{"code":"...","message":"...","request_id":"..."}}` for errors raised through the shared helper. FastAPI validation errors use FastAPI's default validation response.

## Suggested report structure (create your own PDF)

1. Problem and scope / assumptions
2. Service decomposition and rejected alternatives
3. Component diagram and sequence diagram (happy path + payment-failure path)
4. Separate data ownership / ER diagrams
5. API table and OpenAPI links
6. Concurrency, idempotency, and resilience: design, evidence, limitations
7. Test strategy and results
8. Three design trade-offs
9. Limitations and future work
10. Demo video link
Appendix: team contribution table, individual reflection, AI-use declaration.

## Limitations to discuss honestly

- SQLite is used to keep setup simple; production would normally use a server database with appropriate isolation and operational controls.
- The booking orchestration holds a local SQLite write transaction while making downstream HTTP calls to make same-key requests serialize in this teaching implementation. This is simple for a demo but undesirable for high-throughput production; a durable workflow/saga with explicit states would be better.
- The booking and inventory services cannot share a distributed ACID transaction. Compensation handles the simulated payment-failure path, but a process crash between remote operations can require reconciliation.
- Notification is best-effort after payment and is not backed by an outbox/retry worker.
- Authentication, UI, real payment processing, and production deployment are out of scope as requested by the assignment.
