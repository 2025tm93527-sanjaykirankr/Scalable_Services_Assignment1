# Challenge 3A resilience evidence

Run recorded on 2026-10-26 in Asia/Kolkata using isolated SQLite files in this folder.

| Claim | Evidence |
|---|---|
| Payment was stopped, booking made two bounded retries, then returned HTTP 503. | [resilience-run.txt](resilience-run.txt), [booking-service.log](booking-service.log) |
| The failed booking was marked `FAILED`; the reservation became `RELEASED`; `slot-1` capacity was restored to 5. | [resilience-run.txt](resilience-run.txt), [database-states.json](database-states.json) |
| Restarting payment allowed a new booking to complete and created one payment record. | [resilience-run.txt](resilience-run.txt), [payment-service.log](payment-service.log) |
| The payment mock's idempotency behavior and record counts are exercised separately. | [Challenge 2 evidence](../challenge-2-idempotency/README.md) |
| Repeat this run from the repository root. | `python evidence/challenge-3a-resilience/run_evidence.py` |

The payment key is derived from the booking ID, so retries for one booking use the same charge key. The outage run proves timeout/retry and compensation; the payment mock's repeated-key behavior is supported by Challenge 2. The demo still has a crash window between remote calls and local persistence, so it is not a durable production saga.

**Still needed for submission:** the brief asks for a timestamped screenshot showing the command and output. Raw output and service logs are saved here; no screenshot has been added yet.
