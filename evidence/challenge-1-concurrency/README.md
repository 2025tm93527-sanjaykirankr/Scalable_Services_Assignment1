# Challenge 1 concurrency evidence

Run recorded on 2026-10-26 in Asia/Kolkata using isolated SQLite files in this folder.

| Claim | Evidence |
|---|---|
| The repeatable script sent 20 parallel booking requests and received exactly one HTTP 201 and nineteen HTTP 409 responses. | [concurrency-run.txt](concurrency-run.txt) |
| Inventory ended with capacity 1, remaining 0, and one active reservation for `slot-2`. | [final-database-state.txt](final-database-state.txt); database: `challenge1_inventory.db` |
| Inventory accepted one reservation and rejected the other nineteen. | [inventory-service.log](inventory-service.log) |
| Repeat the evidence run from the repository root. It starts all four services with isolated databases, runs the challenge script, records database state, and stops the services. | `python evidence/challenge-1-concurrency/run_evidence.py` |

The inventory service uses an atomic conditional update (`remaining > 0`) inside a SQLite write transaction. A plain check-then-update in application code can let concurrent requests all observe the same remaining unit before any decrement is written, allowing over-allocation.

**Still needed for submission:** the brief asks for a timestamped screenshot showing the command and output. The text output and service logs are saved here; no screenshot has been added yet.
