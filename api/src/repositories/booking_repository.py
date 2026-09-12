from datetime import datetime

from psycopg import errors
from psycopg_pool import ConnectionPool


class BookingRepository:

    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def create(self, timestamp: datetime, telephone: str):
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(
                        """
                        INSERT INTO booking (timestamp, telephone)
                        VALUES (%s, %s)
                        RETURNING id, timestamp, telephone
                        """,
                        (timestamp, telephone),
                    )

                    booking = cursor.fetchone()
                    connection.commit()

                    return booking

                except errors.UniqueViolation:
                    connection.rollback()
                    raise

    def get_by_id(self, booking_id: int):
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, timestamp, telephone
                    FROM booking
                    WHERE id = %s
                    """,
                    (booking_id,),
                )

                return cursor.fetchone()

    def delete(self, booking_id: int):
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM booking
                    WHERE id = %s
                    """,
                    (booking_id,),
                )

                deleted = cursor.rowcount > 0

                connection.commit()

                return deleted

    def update(self, booking_id: int, timestamp: datetime | None = None, telephone: str | None = None):
        # build dynamic SET clause depending on provided values
        fields = []
        params = []

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
                    cursor.execute(
                        f"""
                        UPDATE booking
                        SET {set_clause}
                        WHERE id = %s
                        RETURNING id, timestamp, telephone
                        """,
                        tuple(params),
                    )

                    updated = cursor.fetchone()
                    connection.commit()

                    return updated

                except errors.UniqueViolation:
                    connection.rollback()
                    raise