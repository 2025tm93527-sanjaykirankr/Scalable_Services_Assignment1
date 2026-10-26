"""Run Challenge 1 against isolated local service databases and save raw evidence."""
from __future__ import annotations

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
SERVICES = [
    ("inventory", 8001, "inventory-service", "INVENTORY_DB", "challenge1_inventory.db"),
    ("payment", 8002, "payment-mock-service", "PAYMENT_DB", "challenge1_payment.db"),
    ("notification", 8003, "notification-mock-service", "NOTIFICATION_DB", "challenge1_notification.db"),
    ("booking", 8000, "booking-service", "BOOKING_DB", "challenge1_booking.db"),
]


def timestamp() -> str:
    kolkata = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")
    return datetime.now(kolkata).isoformat(timespec="seconds")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    processes: list[tuple[str, subprocess.Popen, object]] = []
    opened_logs = []
    try:
        for name, port, *_ in SERVICES:
            with socket.socket() as sock:
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    raise RuntimeError(f"Port {port} is already in use; stop that service and rerun.")

        for name, port, folder, db_var, db_name in SERVICES:
            env = os.environ.copy()
            env[db_var] = str(OUT / db_name)
            log_handle = (OUT / f"{name}-service.log").open("w", encoding="utf-8")
            opened_logs.append(log_handle)
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=ROOT / "services" / folder,
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
            )
            processes.append((name, proc, log_handle))

        started = timestamp()
        for name, port, *_ in SERVICES:
            url = f"http://127.0.0.1:{port}/health"
            for _ in range(80):
                try:
                    response = requests.get(url, timeout=0.5)
                    if response.ok:
                        break
                except requests.RequestException:
                    pass
                time.sleep(0.25)
            else:
                raise RuntimeError(f"{name} service failed to become healthy at {url}")

        command = [sys.executable, str(ROOT / "scripts" / "concurrency_test.py")]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
        run_text = (
            f"Timestamp (Asia/Kolkata): {timestamp()}\n"
            f"Command: {' '.join(command)}\n"
            f"Exit code: {result.returncode}\n\n"
            f"{result.stdout}"
            f"{result.stderr}"
        )
        (OUT / "concurrency-run.txt").write_text(run_text, encoding="utf-8")

        db_path = OUT / "challenge1_inventory.db"
        with sqlite3.connect(db_path) as con:
            slot = con.execute(
                "SELECT slot_id, capacity, remaining FROM slots WHERE slot_id='slot-2'"
            ).fetchone()
            reservations = con.execute(
                "SELECT COUNT(*) FROM reservations WHERE slot_id='slot-2' AND status='RESERVED'"
            ).fetchone()[0]
        state = (
            f"Timestamp (Asia/Kolkata): {timestamp()}\n"
            f"Database: {db_path}\n"
            f"slot-2 (slot_id, capacity, remaining): {slot}\n"
            f"Reserved slot-2 reservation count: {reservations}\n"
        )
        (OUT / "final-database-state.txt").write_text(state, encoding="utf-8")
        summary = (
            f"Challenge 1 evidence run\nStarted: {started}\nFinished: {timestamp()}\n"
            f"Concurrency script exit code: {result.returncode}\n"
            f"Final slot state: {slot}; active reservations: {reservations}\n"
        )
        (OUT / "run-summary.txt").write_text(summary, encoding="utf-8")
        print(summary, end="")
        print(f"Saved raw output: {OUT / 'concurrency-run.txt'}")
        print(f"Saved database state: {OUT / 'final-database-state.txt'}")
        return result.returncode if result.returncode else (0 if slot == ("slot-2", 1, 0) and reservations == 1 else 1)
    finally:
        for _name, proc, _handle in reversed(processes):
            proc.terminate()
        for _name, proc, _handle in reversed(processes):
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        for handle in opened_logs:
            handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
