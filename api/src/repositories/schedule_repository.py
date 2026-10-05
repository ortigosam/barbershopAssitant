"""Persistence operations for weekly hours and date exceptions."""

import json

from src.domain.calendar import Calendar, RuleError


class PostgresScheduleRepository:
    def __init__(self, connection):
        self.connection = connection

    def get(self):
        row = self.connection.execute(
            "SELECT weekly, exceptions, version FROM calendar_settings WHERE id=1"
        ).fetchone()
        if not row:
            raise RuleError("NOT_CONFIGURED", "El calendario no está configurado.", 503)
        return Calendar(
            {int(k): [tuple(w) for w in v] for k, v in row[0].items()},
            {k: [tuple(w) for w in v] for k, v in row[1].items()},
        ), row[2]

    def save(self, calendar):
        self.connection.execute(
            "UPDATE calendar_settings SET weekly=%s::jsonb, exceptions=%s::jsonb, "
            "version=version+1 WHERE id=1",
            (json.dumps(calendar.weekly), json.dumps(calendar.exceptions)),
        )
