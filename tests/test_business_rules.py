"""Service-level business rule tests using isolated SQLite databases."""
import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body
        self.text = json.dumps(body)
        self.headers = {}

    def json(self):
        return self.body


def response_data(response):
    if isinstance(response, JSONResponse):
        return response.status_code, json.loads(response.body)
    return 200, response


def request():
    return Request({"type": "http", "method": "POST", "path": "/test", "headers": []})


def query_one(database, sql):
    con = sqlite3.connect(database)
    try:
        return con.execute(sql).fetchone()
    finally:
        con.close()


def load_service(service_dir, module_prefix, db_variable, db_path):
    service_path = ROOT / "services" / service_dir
    sys.path.insert(0, str(service_path))
    os.environ[db_variable] = str(db_path)
    module_name = f"{module_prefix}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, service_path / "app.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    # booking-service initializes its schema at module scope; close that setup
    # connection so temporary SQLite files can be removed on Windows.
    initial_connection = vars(module).get("con")
    if isinstance(initial_connection, sqlite3.Connection):
        initial_connection.close()
    return module


class BusinessRuleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="booking-br-tests-")
        root = Path(self.temp.name)
        self.inventory = load_service(
            "inventory-service", "test_inventory", "INVENTORY_DB", root / "inventory.db"
        )
        self.booking = load_service(
            "booking-service", "test_booking", "BOOKING_DB", root / "booking.db"
        )
        self.events = []

        def downstream(method, url, rid, payload=None, timeout=1.5):
            if "/reserve" in url:
                self.events.append("reserve")
                slot_id = url.split("/slots/")[1].split("/")[0]
                result = self.inventory.reserve(
                    slot_id, self.inventory.ReserveInput(**payload), request()
                )
                status, body = response_data(result)
                return FakeResponse(status, body)
            if "/release" in url:
                self.events.append("release")
                slot_id = url.split("/slots/")[1].split("/")[0]
                result = self.inventory.release(
                    slot_id, self.inventory.ReleaseInput(**payload), request()
                )
                status, body = response_data(result)
                return FakeResponse(status, body)
            if "/notifications" in url:
                self.events.append("notification")
                return FakeResponse(200, {"status": "RECORDED"})
            raise AssertionError(f"Unexpected downstream URL: {url}")

        self.booking.downstream = downstream
        self.booking.payment_with_retry = self.payment_success

    def tearDown(self):
        self.temp.cleanup()

    def payment_success(self, booking_id, amount, rid):
        self.events.append("payment")
        return FakeResponse(200, {
            "payment_id": f"payment-{booking_id}",
            "booking_id": booking_id,
            "amount": amount,
            "status": "CHARGED",
        })

    def test_br1_inventory_never_overallocates_last_slot(self):
        first = self.inventory.reserve("slot-2", self.inventory.ReserveInput(booking_id="one"), request())
        second = self.inventory.reserve("slot-2", self.inventory.ReserveInput(booking_id="two"), request())
        status, body = response_data(second)
        remaining = query_one(self.inventory.DB, "SELECT remaining FROM slots WHERE slot_id='slot-2'")[0]
        reservations = query_one(self.inventory.DB, "SELECT COUNT(*) FROM reservations WHERE slot_id='slot-2'")[0]
        self.assertEqual(first["status"], "RESERVED")
        self.assertEqual(status, 409)
        self.assertEqual(body["error"]["code"], "SLOT_FULL")
        self.assertEqual((remaining, reservations), (0, 1))

    def test_br2_requires_valid_fields_positive_amount_and_idempotency_key(self):
        with self.assertRaises(ValidationError):
            self.booking.BookingInput(customer_id="c", slot_id="slot-1", amount=0)
        with self.assertRaises(ValidationError):
            self.booking.BookingInput(customer_id="", slot_id="slot-1", amount=5)
        body = self.booking.BookingInput(customer_id="c", slot_id="slot-1", amount=5)
        status, data = response_data(self.booking.create_booking(body, request(), None))
        self.assertEqual(status, 400)
        self.assertEqual(data["error"]["code"], "IDEMPOTENCY_KEY_REQUIRED")
        self.assertEqual(self.events, [])

    def test_br3_same_key_replays_one_result_and_changed_payload_conflicts(self):
        body = self.booking.BookingInput(customer_id="c", slot_id="slot-1", amount=10)
        first = self.booking.create_booking(body, request(), "key-1")
        first_status, first_body = response_data(first)
        replay = self.booking.create_booking(body, request(), "key-1")
        replay_status, replay_body = response_data(replay)
        changed = self.booking.BookingInput(customer_id="c", slot_id="slot-1", amount=11)
        changed_status, changed_body = response_data(
            self.booking.create_booking(changed, request(), "key-1")
        )
        bookings = query_one(self.booking.DB, "SELECT COUNT(*) FROM bookings")[0]
        self.assertEqual(first_status, replay_status)
        self.assertEqual(first_body, replay_body)
        self.assertEqual(replay.headers.get("Idempotency-Replayed"), "true")
        self.assertEqual(changed_status, 409)
        self.assertEqual(changed_body["error"]["code"], "IDEMPOTENCY_CONFLICT")
        self.assertEqual(bookings, 1)
        self.assertEqual(self.events.count("payment"), 1)

    def test_br4_payment_failure_releases_inventory_reservation(self):
        def payment_failure(booking_id, amount, rid):
            self.events.append("payment")
            raise RuntimeError("simulated payment outage")

        self.booking.payment_with_retry = payment_failure
        body = self.booking.BookingInput(customer_id="c", slot_id="slot-1", amount=10)
        status, data = response_data(
            self.booking.create_booking(body, request(), "failure-key")
        )
        remaining = query_one(self.inventory.DB, "SELECT remaining FROM slots WHERE slot_id='slot-1'")[0]
        reservation_status = query_one(self.inventory.DB, "SELECT status FROM reservations")[0]
        booking_status = query_one(self.booking.DB, "SELECT status FROM bookings")[0]
        self.assertEqual(status, 503)
        self.assertEqual(data["error"]["code"], "PAYMENT_FAILED")
        self.assertEqual((remaining, reservation_status, booking_status), (5, "RELEASED", "FAILED"))
        self.assertIn("release", self.events)
        self.assertNotIn("notification", self.events)

    def test_br5_notification_is_attempted_only_after_successful_payment(self):
        body = self.booking.BookingInput(customer_id="c", slot_id="slot-1", amount=10)
        status, response = response_data(
            self.booking.create_booking(body, request(), "success-key")
        )
        self.assertEqual(status, 201)
        self.assertEqual(response["status"], "CONFIRMED")
        self.assertEqual(self.events, ["reserve", "payment", "notification"])


if __name__ == "__main__":
    unittest.main()
