from datetime import datetime
from uuid import uuid4

import pytest
from calendar_memory import MemoryStore
from src.application.calendar_service import CalendarService
from src.domain.calendar import RuleError, phone

A = "+34600123456"
B = "+447700900123"


@pytest.fixture
def app():
    result = CalendarService(MemoryStore(), clock=lambda: datetime(2026, 10, 2, 9))
    result.save_customer(A, "Ana")
    result.save_customer(B, "Ben")
    return result


def reserve(app, day=5, hour=10, minute=0, count=1, actor=A, key=None):
    return app.reserve(
        actor, datetime(2026, 10, day, hour, minute), count, key or str(uuid4())
    )["bookings"]


def test_international_identity():
    assert phone("600 123-456") == A
    assert phone("0034 600123456") == A
    assert phone("+44 7700 900123") == B
    with pytest.raises(RuleError):
        phone("abc")


def test_twenty_minute_calendar(app):
    slots = app.availability("next")["slots"]
    assert {"timestamp": "2026-10-05T20:40:00"} in slots
    assert {"timestamp": "2026-10-05T21:00:00"} not in slots
    assert {"timestamp": "2026-10-10T13:40:00"} in slots
    assert {"timestamp": "2026-10-10T17:00:00"} not in slots
    with pytest.raises(RuleError):
        reserve(app, day=12)
    with pytest.raises(RuleError):
        reserve(app, minute=30)


def test_cancel_releases_slot_and_receipt_cannot_recreate(app):
    key = str(uuid4())
    booking = reserve(app, key=key)[0]
    app.cancel(A, booking["id"])
    assert not app.list_bookings(A)
    reserve(app, actor=B)
    with pytest.raises(RuleError):
        reserve(app, key=key)


def test_batch_rollback_and_monthly_quota(app):
    reserve(app, minute=40, actor=B)
    with pytest.raises(RuleError):
        reserve(app, count=3)
    assert app.list_bookings(A) == []
    batch = reserve(app, hour=12, count=5)
    with pytest.raises(RuleError):
        reserve(app, day=6)
    app.cancel(A, batch[0]["id"])
    reserve(app, day=6)


def test_owner_checks(app):
    booking = reserve(app)[0]
    for action in [
        lambda: app.get(B, booking["id"]),
        lambda: app.cancel(B, booking["id"]),
    ]:
        with pytest.raises(RuleError) as error:
            action()
        assert error.value.status == 404


def test_cutoff_and_completed(app):
    booking = reserve(app)[0]
    app.clock = lambda: datetime(2026, 10, 5, 10)
    with pytest.raises(RuleError):
        app.cancel(A, booking["id"])
    assert app.get(A, booking["id"])["status"] == "confirmed"
    app.clock = lambda: datetime(2026, 10, 5, 10, 20)
    assert app.get(A, booking["id"])["status"] == "completed"


def test_schedule_changes_are_versioned_and_cannot_strand_appointments(app):
    reserve(app)
    config = app.settings()
    config["exceptions"]["2026-10-05"] = []
    with pytest.raises(RuleError):
        app.save_settings(**config)
    assert not app.settings()["exceptions"]
    config["exceptions"] = {"2026-10-06": []}
    app.save_settings(**config)
    assert not any(
        s["timestamp"].startswith("2026-10-06")
        for s in app.availability("next")["slots"]
    )
    with pytest.raises(RuleError):
        app.save_settings(**config)


def test_idempotency_and_started_count_in_quota(app):
    key = str(uuid4())
    original = reserve(app, count=5, key=key)
    assert reserve(app, count=5, key=key) == original
    app.clock = lambda: datetime(2026, 10, 5, 14)
    with pytest.raises(RuleError):
        reserve(app, day=6)


def test_batch_cannot_cross_lunch(app):
    with pytest.raises(RuleError):
        reserve(app, hour=13, minute=40, count=2)


def test_name_changes(app):
    app.save_customer(A, "Ana María")
    assert app.customer(A)["name"] == "Ana María"
