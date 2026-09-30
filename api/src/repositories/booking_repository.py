from datetime import datetime
from typing import Any, Optional, Tuple, cast, List

from typing_extensions import LiteralString

from psycopg import Connection, errors
from psycopg_pool import ConnectionPool


Row = Tuple[int, datetime, str]


class BookingRepository:

    def __init__(self, pool: ConnectionPool[Connection[Any]]):
        self.pool: ConnectionPool[Connection[Any]] = pool

    def create(self, timestamp: datetime, telephone: str) -> Row:
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                try:
                    qry: LiteralString = """
                    INSERT INTO booking (timestamp, telephone)
                    VALUES (%s, %s)
                    RETURNING id, timestamp, telephone
                    """
                    cursor.execute(qry, (timestamp, telephone))

                    booking = cast(Optional[Row], cursor.fetchone())
                    connection.commit()

                    # booking is (id, timestamp, telephone)
                    assert booking is not None
                    return booking

                except errors.UniqueViolation:
                    connection.rollback()
                    raise

    def get_by_id(self, booking_id: int) -> Optional[Row]:
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                qry: LiteralString = """
                SELECT id, timestamp, telephone
                FROM booking
                WHERE id = %s
                """
                cursor.execute(qry, (booking_id,))

                return cast(Optional[Row], cursor.fetchone())

    def list_between(self, start: datetime, end: datetime) -> list[Row]:
        """Return bookings in the half-open interval ``[start, end)``."""
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                qry: LiteralString = """
                SELECT id, timestamp, telephone
                FROM booking
                WHERE timestamp >= %s AND timestamp < %s
                ORDER BY timestamp
                """
                cursor.execute(qry, (start, end))
                return cast(list[Row], cursor.fetchall())

    def delete(self, booking_id: int) -> bool:
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                qry: LiteralString = """
                DELETE FROM booking
                WHERE id = %s
                """
                cursor.execute(qry, (booking_id,))

                deleted = cursor.rowcount > 0

                connection.commit()

                return deleted

    def update(
        self,
        booking_id: int,
        timestamp: datetime | None = None,
        telephone: str | None = None,
    ) -> Optional[Row]:
        # build dynamic SET clause depending on provided values
        fields: List[str] = []
        params: List[Any] = []

        if timestamp is not None:
            fields.append("timestamp = %s")
            params.append(timestamp)

        if telephone is not None:
            fields.append("telephone = %s")
            params.append(telephone)

        if not fields:
            # nothing to update, return current record
            return self.get_by_id(booking_id)

        params.append(booking_id)

        set_clause = ", ".join(fields)

        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                try:
                    # dynamic SQL because SET clause is built at runtime; use a
                    # targeted type ignore for the execute arg-type here so
                    # Pylance doesn't complain about QueryNoTemplate expectations.
                    cursor.execute(
                        f"""
                        UPDATE booking
                        SET {set_clause}
                        WHERE id = %s
                        RETURNING id, timestamp, telephone
                        """,
                        tuple(params),
                    )  # type: ignore[arg-type]

                    updated = cast(Optional[Row], cursor.fetchone())
                    connection.commit()

                    return updated

                except errors.UniqueViolation:
                    connection.rollback()
                    raise
