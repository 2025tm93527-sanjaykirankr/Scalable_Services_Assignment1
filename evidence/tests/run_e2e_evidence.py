"""Run the repository's end-to-end script against isolated local databases."""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUN_ID = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y%m%d-%H%M%S-%f")
SERVICES = [
    ("inventory", 8001, "inventory-service", "INVENTORY_DB", f"{RUN_ID}_e2e_inventory.db"),
    ("payment", 8002, "payment-mock-service", "PAYMENT_DB", f"{RUN_ID}_e2e_payment.db"),
    ("notification", 8003, "notification-mock-service", "NOTIFICATION_DB", f"{RUN_ID}_e2e_notification.db"),
    ("booking", 8000, "booking-service", "BOOKING_DB", f"{RUN_ID}_e2e_booking.db"),
]


def timestamp() -> str:
    return datetime.now(timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")).isoformat(timespec="seconds")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    processes = []
    logs = []
    try:
        for name, port, *_ in SERVICES:
            with socket.socket() as sock:
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    raise RuntimeError(f"Port {port} is already in use; stop that service and rerun.")
        started = timestamp()
        for name, port, folder, db_var, db_file in SERVICES:
            env = os.environ.copy()
            env[db_var] = str(OUT / db_file)
            log = (OUT / f"{name}-e2e-service.log").open("w", encoding="utf-8")
            logs.append(log)
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=ROOT / "services" / folder, env=env, stdout=log, stderr=subprocess.STDOUT,
            )
            processes.append(proc)
        for _name, port, *_ in SERVICES:
            url = f"http://127.0.0.1:{port}/health"
            for _ in range(80):
                try:
                    if requests.get(url, timeout=0.5).ok:
                        break
                except requests.RequestException:
                    pass
                time.sleep(0.25)
            else:
                raise RuntimeError(f"Service failed to become healthy: {url}")

        command = [sys.executable, str(ROOT / "scripts" / "e2e_test.py")]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
        checks = {}
        for service, db, sqls in [
            ("booking", f"{RUN_ID}_e2e_booking.db", {"confirmed_bookings": "SELECT COUNT(*) FROM bookings WHERE status='CONFIRMED'", "idempotency_rows": "SELECT COUNT(*) FROM idempotency"}),
            ("inventory", f"{RUN_ID}_e2e_inventory.db", {"reservations": "SELECT COUNT(*) FROM reservations WHERE status='RESERVED'", "slot_1": "SELECT remaining FROM slots WHERE slot_id='slot-1'"}),
            ("payment", f"{RUN_ID}_e2e_payment.db", {"payments": "SELECT COUNT(*) FROM payments"}),
            ("notification", f"{RUN_ID}_e2e_notification.db", {"notifications": "SELECT COUNT(*) FROM notifications"}),
        ]:
            with sqlite3.connect(OUT / db) as con:
                checks[service] = {key: con.execute(sql).fetchone()[0] for key, sql in sqls.items()}
        passed = result.returncode == 0 and checks == {
            "booking": {"confirmed_bookings": 1, "idempotency_rows": 1},
            "inventory": {"reservations": 1, "slot_1": 4},
            "payment": {"payments": 1},
            "notification": {"notifications": 1},
        }
        output = (
            f"Timestamp (Asia/Kolkata): {timestamp()}\n"
            f"Command: {' '.join(command)}\nStarted: {started}\nExit code: {result.returncode}\n\n"
            f"{result.stdout}{result.stderr}\n"
            f"Isolated database files: {json.dumps({name: db_file for name, _port, _folder, _var, db_file in SERVICES}, sort_keys=True)}\n"
            f"Database checks:\n{json.dumps(checks, indent=2, sort_keys=True)}\n"
            f"Result: {'PASS' if passed else 'FAIL'}\n"
        )
        (OUT / "e2e-run.txt").write_text(output, encoding="utf-8")
        (OUT / "e2e-database-checks.json").write_text(json.dumps({
            "timestamp": timestamp(),
            "databases": {name: db_file for name, _port, _folder, _var, db_file in SERVICES},
            "checks": checks,
        }, indent=2) + "\n", encoding="utf-8")
        summary = f"End-to-end evidence run\nStarted: {started}\nFinished: {timestamp()}\nScript exit code: {result.returncode}\nCross-service database checks: {'PASS' if passed else 'FAIL'}\nResult: {'PASS' if passed else 'FAIL'}\n"
        (OUT / "e2e-summary.txt").write_text(summary, encoding="utf-8")
        print(summary, end="")
        print(f"Saved output: {OUT / 'e2e-run.txt'}")
        return 0 if passed else 1
    finally:
        for proc in reversed(processes):
            if proc.poll() is None:
                proc.terminate()
        for proc in reversed(processes):
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        for log in logs:
            log.close()


if __name__ == "__main__":
    raise SystemExit(main())
