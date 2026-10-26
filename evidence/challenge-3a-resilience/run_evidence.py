"""Capture bounded retry, graceful payment failure, compensation and recovery."""
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
SERVICES = [
    ("inventory", 8001, "inventory-service", "INVENTORY_DB", "challenge3a_inventory.db"),
    ("payment", 8002, "payment-mock-service", "PAYMENT_DB", "challenge3a_payment.db"),
    ("notification", 8003, "notification-mock-service", "NOTIFICATION_DB", "challenge3a_notification.db"),
    ("booking", 8000, "booking-service", "BOOKING_DB", "challenge3a_booking.db"),
]
KOLKATA = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")


def timestamp() -> str:
    return datetime.now(KOLKATA).isoformat(timespec="seconds")


def launch(name, port, folder, db_var, db_file, *, append=False):
    env = os.environ.copy()
    env[db_var] = str(OUT / db_file)
    log = (OUT / f"{name}-service.log").open("a" if append else "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT / "services" / folder, env=env,
        stdout=log, stderr=subprocess.STDOUT,
    )
    return proc, log


def wait_health(port: int, attempts: int = 80) -> None:
    url = f"http://127.0.0.1:{port}/health"
    for _ in range(attempts):
        try:
            if requests.get(url, timeout=0.5).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(0.25)
    raise RuntimeError(f"Service failed to become healthy at {url}")


def db_state() -> dict:
    state = {}
    with sqlite3.connect(OUT / "challenge3a_inventory.db") as con:
        state["slot_1"] = con.execute(
            "SELECT capacity, remaining FROM slots WHERE slot_id='slot-1'"
        ).fetchone()
        state["reservations"] = con.execute(
            "SELECT status, COUNT(*) FROM reservations GROUP BY status ORDER BY status"
        ).fetchall()
    with sqlite3.connect(OUT / "challenge3a_booking.db") as con:
        state["bookings"] = con.execute(
            "SELECT status, COUNT(*) FROM bookings GROUP BY status ORDER BY status"
        ).fetchall()
    with sqlite3.connect(OUT / "challenge3a_payment.db") as con:
        state["payments"] = con.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    return state


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    processes: dict[str, subprocess.Popen] = {}
    handles = []
    try:
        for name, port, *_ in SERVICES:
            with socket.socket() as sock:
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    raise RuntimeError(f"Port {port} is already in use; stop that service and rerun.")

        for name, port, folder, db_var, db_file in SERVICES:
            proc, log = launch(name, port, folder, db_var, db_file)
            processes[name] = proc
            handles.append(log)
        started = timestamp()
        for _name, port, *_ in SERVICES:
            wait_health(port)

        processes["payment"].terminate()
        processes["payment"].wait(timeout=5)
        failed_request = requests.post(
            "http://127.0.0.1:8000/api/v1/bookings",
            headers={"Idempotency-Key": "evidence-payment-outage"},
            json={"customer_id": "resilience-demo", "slot_id": "slot-1", "amount": 31.0},
            timeout=20,
        )
        after_failure = db_state()

        payment_cfg = next(item for item in SERVICES if item[0] == "payment")
        payment_proc, payment_log = launch(*payment_cfg, append=True)
        processes["payment"] = payment_proc
        handles.append(payment_log)
        wait_health(8002)
        recovery_request = requests.post(
            "http://127.0.0.1:8000/api/v1/bookings",
            headers={"Idempotency-Key": "evidence-payment-recovery"},
            json={"customer_id": "resilience-demo", "slot_id": "slot-1", "amount": 31.0},
            timeout=20,
        )
        after_recovery = db_state()

        passed = (
            failed_request.status_code == 503
            and after_failure["slot_1"] == (5, 5)
            and after_failure["reservations"] == [("RELEASED", 1)]
            and after_failure["bookings"] == [("FAILED", 1)]
            and after_failure["payments"] == 0
            and recovery_request.status_code == 201
            and recovery_request.json().get("status") == "CONFIRMED"
            and after_recovery["payments"] == 1
        )
        text = [
            f"Timestamp (Asia/Kolkata): {timestamp()}",
            "Command: python evidence/challenge-3a-resilience/run_evidence.py",
            f"Started: {started}",
            "",
            "Stopped payment-mock-service before this request.",
            f"Failure request: HTTP {failed_request.status_code}; body={json.dumps(failed_request.json(), sort_keys=True)}",
            f"Database state after failure and compensation: {json.dumps(after_failure, sort_keys=True)}",
            "",
            "Restarted payment-mock-service and sent a new request with a new idempotency key.",
            f"Recovery request: HTTP {recovery_request.status_code}; body={json.dumps(recovery_request.json(), sort_keys=True)}",
            f"Database state after recovery: {json.dumps(after_recovery, sort_keys=True)}",
            "",
            f"Result: {'PASS' if passed else 'FAIL'}",
        ]
        (OUT / "resilience-run.txt").write_text("\n".join(text) + "\n", encoding="utf-8")
        summary = (
            f"Challenge 3A evidence run\nStarted: {started}\nFinished: {timestamp()}\n"
            f"Payment outage returned 503: {failed_request.status_code == 503}\n"
            f"Reservation released and capacity restored: {after_failure['slot_1'] == (5, 5) and after_failure['reservations'] == [('RELEASED', 1)]}\n"
            f"Recovery booking succeeded with one payment record: {recovery_request.status_code == 201 and after_recovery['payments'] == 1}\n"
            f"Result: {'PASS' if passed else 'FAIL'}\n"
        )
        (OUT / "run-summary.txt").write_text(summary, encoding="utf-8")
        (OUT / "database-states.json").write_text(json.dumps({"after_failure": after_failure, "after_recovery": after_recovery}, indent=2, default=list) + "\n", encoding="utf-8")
        print(summary, end="")
        print(f"Saved output: {OUT / 'resilience-run.txt'}")
        print(f"Saved booking log: {OUT / 'booking-service.log'}")
        return 0 if passed else 1
    finally:
        for proc in processes.values():
            if proc.poll() is None:
                proc.terminate()
        for proc in processes.values():
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
