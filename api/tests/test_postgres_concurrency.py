"""Integration tests in a disposable schema; never use live application tables."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1", reason="Requires PostgreSQL"
)


@pytest.fixture
def app():
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    from psycopg_pool import ConnectionPool
    from src.application.calendar_service import CalendarService
    from src.config import settings
    from src.repositories.calendar_store import PostgresCalendarStore

    dsn = make_conninfo(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        dbname=settings.postgres_db,
        connect_timeout=3,
    )
    schema = "test_calendar_" + uuid4().hex
    with psycopg.connect(dsn, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            with ConnectionPool(
                dsn,
                kwargs={"options": f"-c search_path={schema}"},
                min_size=2,
                max_size=4,
            ) as pool:
                with pool.connection() as setup:
                    setup.execute(
                        Path(__file__)
                        .resolve()
                        .parents[2]
                        .joinpath("database/schema.sql")
                        .read_text()
                    )
                service = CalendarService(
                    PostgresCalendarStore(pool), clock=lambda: datetime(2026, 10, 2, 9)
                )
                service.save_customer("+34600123456", "Ana")
                service.save_customer("+447700900123", "Ben")
                yield service
        finally:
            connection.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
            )


def attempt(call):
    from src.domain.calendar import RuleError

    try:
        return call()
    except RuleError as error:
        return error.code


def test_concurrent_slot_and_idempotent_replay(app):
    def reserve(_):
        return attempt(
            lambda: app.reserve(
                "+34600123456", datetime(2026, 10, 5, 10), 1, str(uuid4())
            )
        )

    with ThreadPoolExecutor(2) as ex:
        results = list(ex.map(reserve, range(2)))
    assert sum(isinstance(r, dict) for r in results) == 1
    assert "BOOKING_ALREADY_EXISTS" in results
    key = str(uuid4())
    with ThreadPoolExecutor(2) as ex:
        results = list(
            ex.map(
                lambda _: app.reserve(
                    "+34600123456", datetime(2026, 10, 5, 11), 1, key
                ),
                range(2),
            )
        )
    assert results[0] == results[1]


def test_concurrent_quota_and_cancel_releases(app):
    app.reserve("+34600123456", datetime(2026, 10, 5, 10), 4, str(uuid4()))

    def reserve(hour):
        return attempt(
            lambda: app.reserve(
                "+34600123456", datetime(2026, 10, 5, hour), 1, str(uuid4())
            )
        )

    with ThreadPoolExecutor(2) as ex:
        results = list(ex.map(reserve, (12, 13)))
    assert sum(isinstance(r, dict) for r in results) == 1
    assert "MONTHLY_LIMIT" in results
    booking = app.list_bookings("+34600123456")[0]
    app.cancel("+34600123456", booking["id"])
    app.reserve(
        "+447700900123", datetime.fromisoformat(booking["timestamp"]), 1, str(uuid4())
    )


def test_batch_rolls_back_and_schedule_conflict(app):
    app.reserve("+447700900123", datetime(2026, 10, 5, 10, 40), 1, str(uuid4()))
    assert (
        attempt(
            lambda: app.reserve(
                "+34600123456", datetime(2026, 10, 5, 10), 3, str(uuid4())
            )
        )
        == "BOOKING_ALREADY_EXISTS"
    )
    assert app.list_bookings("+34600123456") == []
    config = app.settings()
    config["exceptions"]["2026-10-05"] = []
    assert attempt(lambda: app.save_settings(**config)) == "SCHEDULE_CONFLICT"
    assert app.settings()["exceptions"] == {}
