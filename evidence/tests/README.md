# Test and end-to-end evidence

## Main transaction

The saved end-to-end run created and retrieved a confirmed booking, then checked that each service recorded its part of the transaction. See [e2e-run.txt](e2e-run.txt), [e2e-database-checks.json](e2e-database-checks.json), and the four `*-e2e-service.log` files. Repeat from the repository root with `python evidence/tests/run_e2e_evidence.py`.

## Business-rule tests

The standard-library `unittest` suite now exercises BR1–BR5 through the inventory and booking service functions with isolated SQLite databases. It checks slot exhaustion, request validation and required idempotency keys, same-key replay and changed-payload conflict, compensation after payment failure, and notification ordering after successful payment. See `tests/test_business_rules.py` and the captured [business-rule test output](business-rule-tests.txt).

Run the suite from the repository root with `python -m unittest discover -s tests -p test_business_rules.py -v`. It passed all five tests on 2026-10-26. Pytest is not installed in this environment, but it is not needed for this unittest command; pytest discovery can also run `unittest.TestCase` tests after pytest is installed.

**Still needed for submission:** timestamped screenshots showing commands and output.
