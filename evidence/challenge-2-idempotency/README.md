# Challenge 2 idempotency evidence

Run recorded on 2026-10-26 in Asia/Kolkata. The runner uses isolated SQLite files in this folder.

| Claim | Evidence |
|---|---|
| First call returned HTTP 201 and an exact sequential replay returned the same body with `Idempotency-Replayed: true`. | [idempotency-run.txt](idempotency-run.txt) |
| Reusing the sequential key with a changed amount returned HTTP 409. | [idempotency-run.txt](idempotency-run.txt) |
| Twenty simultaneous identical calls returned HTTP 201 with identical bodies; nineteen were marked as replays. | [idempotency-run.txt](idempotency-run.txt), [booking-service.log](booking-service.log) |
| The two distinct keys produced two bookings, two idempotency rows, two reservations, two payments, and two notifications total. | [database-record-counts.json](database-record-counts.json); isolated databases: `challenge2_*.db` |
| Repeat the run from the repository root. | `python evidence/challenge-2-idempotency/run_evidence.py` |

Booking stores a canonical request fingerprint and response under a unique idempotency key. `BEGIN IMMEDIATE` serializes concurrent requests in this SQLite demo; requests that find the stored key return the saved response instead of creating another booking. The payment service also uses a unique charge key, while inventory and notification records are unique by booking ID.

**Still needed for submission:** the brief asks for a timestamped screenshot showing the command and output. Raw output and service logs are saved here; no screenshot has been added yet.
