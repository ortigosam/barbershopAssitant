"""PostgreSQL adapter. All calendar mutations share a transaction lock.

At one-barber scale serialization is simple and guarantees that slot checks,
monthly quotas, schedule changes and batches are committed together.
"""

import json
from contextlib import contextmanager

from psycopg import errors
from src.domain.calendar import Appointment, Calendar, RuleError

LOCK_ID = 78204312


class PostgresBarbershopStore:
    def __init__(self, pool):
        self.pool = pool

    @contextmanager
    def transaction(self):
        try:
            with self.pool.connection() as connection:
                with connection.transaction():
                    connection.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
                    yield Transaction(connection)
        except errors.UniqueViolation:
            raise RuleError(
                "BOOKING_ALREADY_EXISTS",
                "Ese horario ya no está disponible. Puedo consultar otros horarios.",
                409,
            ) from None
        except errors.ExclusionViolation:
            raise RuleError(
                "BOOKING_ALREADY_EXISTS",
                "Ese horario ya no está disponible. Puedo consultar otros horarios.",
                409,
            ) from None


class Transaction:
    def __init__(self, connection):
        self.c = connection

    def calendar(self):
        row = self.c.execute(
            "SELECT weekly, exceptions, version FROM calendar_settings WHERE id=1"
        ).fetchone()
        if not row:
            raise RuleError("NOT_CONFIGURED", "El calendario no está configurado.", 503)
        return Calendar(
            {int(k): [tuple(w) for w in v] for k, v in row[0].items()},
            {k: [tuple(w) for w in v] for k, v in row[1].items()},
        ), row[2]

    def save_calendar(self, calendar):
        self.c.execute(
            "UPDATE calendar_settings SET weekly=%s::jsonb, exceptions=%s::jsonb, version=version+1 WHERE id=1",
            (json.dumps(calendar.weekly), json.dumps(calendar.exceptions)),
        )

    def customer(self, telephone):
        row = self.c.execute(
            "SELECT telephone, name FROM client WHERE telephone=%s", (telephone,)
        ).fetchone()
        return dict(telephone=row[0], name=row[1]) if row else None

    def save_customer(self, telephone, name):
        self.c.execute(
            "INSERT INTO client (telephone,name) VALUES (%s,%s) ON CONFLICT(telephone) DO UPDATE SET name=excluded.name",
            (telephone, name),
        )
        return dict(telephone=telephone, name=name)

    def appointments(self, start, end, telephone=None):
        rows = self.c.execute(
            """SELECT a.id,a.timestamp,a.telephone,c.name FROM appointment a JOIN client c USING(telephone)
            WHERE a.timestamp < %s AND a.timestamp + interval '20 minutes' > %s
            AND (%s::text IS NULL OR a.telephone=%s) ORDER BY a.timestamp,a.id""",
            (end, start, telephone, telephone),
        ).fetchall()
        return [Appointment(*row) for row in rows]

    def appointment(self, identifier):
        row = self.c.execute(
            "SELECT a.id,a.timestamp,a.telephone,c.name FROM appointment a JOIN client c USING(telephone) WHERE a.id=%s",
            (identifier,),
        ).fetchone()
        return Appointment(*row) if row else None

    def insert(self, timestamp, telephone):
        row = self.c.execute(
            "INSERT INTO appointment(timestamp,telephone) VALUES(%s,%s) RETURNING id",
            (timestamp, telephone),
        ).fetchone()
        return self.appointment(row[0])

    def move(self, identifier, timestamp):
        self.c.execute(
            "UPDATE appointment SET timestamp=%s WHERE id=%s", (timestamp, identifier)
        )
        return self.appointment(identifier)

    def delete(self, identifier):
        self.c.execute("DELETE FROM appointment WHERE id=%s", (identifier,))
        # Keep only the operation tombstone; no cancelled appointment data.
        self.c.execute(
            "UPDATE calendar_receipt SET ids='[]'::jsonb, invalidated=true WHERE ids @> %s::jsonb",
            (json.dumps([identifier]),),
        )

    def receipt(self, key):
        row = self.c.execute(
            "SELECT fingerprint,ids,invalidated FROM calendar_receipt WHERE request_id=%s",
            (key,),
        ).fetchone()
        return dict(fingerprint=row[0], ids=row[1], invalidated=row[2]) if row else None

    def save_receipt(self, key, fingerprint, ids):
        self.c.execute(
            "INSERT INTO calendar_receipt(request_id,fingerprint,ids) VALUES(%s,%s,%s::jsonb)",
            (key, fingerprint, json.dumps(ids)),
        )


# Compatibility alias for the old module/class name.
PostgresCalendarStore = PostgresBarbershopStore
