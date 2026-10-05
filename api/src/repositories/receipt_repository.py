"""Persistence operations for idempotent booking requests."""

import json


class PostgresReceiptRepository:
    def __init__(self, connection):
        self.connection = connection

    def get(self, request_id):
        row = self.connection.execute(
            "SELECT fingerprint,ids,invalidated FROM calendar_receipt "
            "WHERE request_id=%s",
            (request_id,),
        ).fetchone()
        return (
            {"fingerprint": row[0], "ids": row[1], "invalidated": row[2]}
            if row
            else None
        )

    def save(self, request_id, fingerprint, ids):
        self.connection.execute(
            "INSERT INTO calendar_receipt(request_id,fingerprint,ids) "
            "VALUES(%s,%s,%s::jsonb)",
            (request_id, fingerprint, json.dumps(ids)),
        )

    def invalidate_for_booking(self, identifier):
        self.connection.execute(
            "UPDATE calendar_receipt SET ids='[]'::jsonb, invalidated=true "
            "WHERE ids @> %s::jsonb",
            (json.dumps([identifier]),),
        )
