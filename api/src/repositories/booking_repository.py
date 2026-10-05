"""Persistence operations for appointments."""

from src.domain.calendar import Appointment


class PostgresBookingRepository:
    def __init__(self, connection):
        self.connection = connection

    def list(self, start, end, telephone=None):
        rows = self.connection.execute(
            """SELECT a.id,a.timestamp,a.telephone,c.name FROM appointment a
            JOIN client c USING(telephone)
            WHERE a.timestamp < %s AND a.timestamp + interval '20 minutes' > %s
            AND (%s::text IS NULL OR a.telephone=%s)
            ORDER BY a.timestamp,a.id""",
            (end, start, telephone, telephone),
        ).fetchall()
        return [Appointment(*row) for row in rows]

    def get(self, identifier):
        row = self.connection.execute(
            """SELECT a.id,a.timestamp,a.telephone,c.name FROM appointment a
            JOIN client c USING(telephone) WHERE a.id=%s""",
            (identifier,),
        ).fetchone()
        return Appointment(*row) if row else None

    def create(self, timestamp, telephone):
        row = self.connection.execute(
            "INSERT INTO appointment(timestamp,telephone) VALUES(%s,%s) RETURNING id",
            (timestamp, telephone),
        ).fetchone()
        return self.get(row[0])

    def delete(self, identifier):
        self.connection.execute("DELETE FROM appointment WHERE id=%s", (identifier,))
