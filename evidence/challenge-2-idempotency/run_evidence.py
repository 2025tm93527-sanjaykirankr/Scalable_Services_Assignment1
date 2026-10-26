"""Exercise sequential and concurrent booking idempotency with isolated databases."""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SERVICES = [
    ("inventory", 8001, "inventory-service", "INVENTORY_DB", "challenge2_inventory.db"),
    ("payment", 8002, "payment-mock-service", "PAYMENT_DB", "challenge2_payment.db"),
    ("notification", 8003, "notification-mock-service", "NOTIFICATION_DB", "challenge2_notification.db"),
    ("booking", 8000, "booking-service", "BOOKING_DB", "challenge2_booking.db"),
]
KOLKATA = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")


def timestamp() -> str:
    return datetime.now(KOLKATA).isoformat(timespec="seconds")


def post(key: str, payload: dict) -> requests.Response:
    return requests.post(
        "http://127.0.0.1:8000/api/v1/bookings",
        headers={"Idempotency-Key": key}, json=payload, timeout=30,
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    processes: list[tuple[str, subprocess.Popen, object]] = []
    log_handles = []
    try:
        for name, port, *_ in SERVICES:
            with socket.socket() as sock:
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    raise RuntimeError(f"Port {port} is already in use; stop that service and rerun.")

        for name, port, folder, db_var, db_file in SERVICES:
            env = os.environ.copy()
            env[db_var] = str(OUT / db_file)
            log = (OUT / f"{name}-service.log").open("w", encoding="utf-8")
            log_handles.append(log)
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=ROOT / "services" / folder, env=env,
                stdout=log, stderr=subprocess.STDOUT,
            )
            processes.append((name, proc, log))

        started = timestamp()
        for name, port, *_ in SERVICES:
            url = f"http://127.0.0.1:{port}/health"
            for _ in range(80):
                try:
                    if requests.get(url, timeout=0.5).ok:
                        break
                except requests.RequestException:
                    pass
                time.sleep(0.25)
            else:
                raise RuntimeError(f"{name} service failed to become healthy at {url}")

        payload = {"customer_id": "idem-demo", "slot_id": "slot-1", "amount": 19.5}
        sequential_key = "evidence-sequential-idem"
        first = post(sequential_key, payload)
        replay = post(sequential_key, payload)
        changed = post(sequential_key, {**payload, "amount": 20.0})

        concurrent_key = "evidence-concurrent-idem"
        workers = 20
        with ThreadPoolExecutor(max_workers=workers) as pool:
            concurrent = list(pool.map(lambda _i: post(concurrent_key, payload), range(workers)))
        bodies = [r.json() for r in concurrent]
        concurrent_ok = all(r.status_code == 201 for r in concurrent) and all(b == bodies[0] for b in bodies)
        replay_headers = sum(r.headers.get("Idempotency-Replayed") == "true" for r in concurrent)

        result_lines = [
            f"Timestamp (Asia/Kolkata): {timestamp()}",
            "Command: python evidence/challenge-2-idempotency/run_evidence.py",
            f"Started: {started}",
            "",
            f"Sequential first call: HTTP {first.status_code}; replay header={first.headers.get('Idempotency-Replayed')}; body={json.dumps(first.json(), sort_keys=True)}",
            f"Sequential exact replay: HTTP {replay.status_code}; replay header={replay.headers.get('Idempotency-Replayed')}; body={json.dumps(replay.json(), sort_keys=True)}",
            f"Changed payload with same key: HTTP {changed.status_code}; body={json.dumps(changed.json(), sort_keys=True)}",
            f"Concurrent identical calls: {workers} requests; HTTP statuses={sorted(set(r.status_code for r in concurrent))}; identical response bodies={all(b == bodies[0] for b in bodies)}; replay headers={replay_headers}/{workers}",
            f"Concurrent canonical response: {json.dumps(bodies[0], sort_keys=True)}",
        ]

        counts = {}
        for service_name, db_name, queries in [
            ("booking", "challenge2_booking.db", {"bookings": "SELECT COUNT(*) FROM bookings", "idempotency_keys": "SELECT COUNT(*) FROM idempotency"}),
            ("inventory", "challenge2_inventory.db", {"reservations": "SELECT COUNT(*) FROM reservations WHERE status='RESERVED'"}),
            ("payment", "challenge2_payment.db", {"payments": "SELECT COUNT(*) FROM payments"}),
            ("notification", "challenge2_notification.db", {"notifications": "SELECT COUNT(*) FROM notifications"}),
        ]:
            with sqlite3.connect(OUT / db_name) as con:
                counts[service_name] = {label: con.execute(query).fetchone()[0] for label, query in queries.items()}
        result_lines.extend(["", "Database record counts (two distinct idempotency keys were exercised):", json.dumps(counts, indent=2, sort_keys=True)])
        (OUT / "idempotency-run.txt").write_text("\n".join(result_lines) + "\n", encoding="utf-8")
        (OUT / "database-record-counts.json").write_text(json.dumps({"timestamp": timestamp(), "counts": counts}, indent=2) + "\n", encoding="utf-8")

        expected_counts = {
            "booking": {"bookings": 2, "idempotency_keys": 2},
            "inventory": {"reservations": 2},
            "payment": {"payments": 2},
            "notification": {"notifications": 2},
        }
        passed = (
            first.status_code == 201
            and replay.status_code == 201
            and first.json() == replay.json()
            and replay.headers.get("Idempotency-Replayed") == "true"
            and changed.status_code == 409
            and concurrent_ok
            and counts == expected_counts
        )
        summary = (
            f"Challenge 2 evidence run\nStarted: {started}\nFinished: {timestamp()}\n"
            f"Sequential replay matched: {first.json() == replay.json()}\n"
            f"Changed payload rejected with 409: {changed.status_code == 409}\n"
            f"20 concurrent requests returned one identical result: {concurrent_ok}\n"
            f"One effect per key in each service database: {counts == expected_counts}\n"
            f"Result: {'PASS' if passed else 'FAIL'}\n"
        )
        (OUT / "run-summary.txt").write_text(summary, encoding="utf-8")
        print(summary, end="")
        print(f"Saved output: {OUT / 'idempotency-run.txt'}")
        print(f"Saved database counts: {OUT / 'database-record-counts.json'}")
        return 0 if passed else 1
    finally:
        for _name, proc, _log in reversed(processes):
            proc.terminate()
        for _name, proc, _log in reversed(processes):
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        for log in log_handles:
            log.close()


if __name__ == "__main__":
    raise SystemExit(main())
