"""Persistence operations for customer records."""


class PostgresClientRepository:
    def __init__(self, connection):
        self.connection = connection

    def get(self, telephone):
        row = self.connection.execute(
            "SELECT telephone, name FROM client WHERE telephone=%s", (telephone,)
        ).fetchone()
        return {"telephone": row[0], "name": row[1]} if row else None

    def save(self, telephone, name):
        self.connection.execute(
            "INSERT INTO client (telephone,name) VALUES (%s,%s) "
            "ON CONFLICT(telephone) DO UPDATE SET name=excluded.name",
            (telephone, name),
        )
        return {"telephone": telephone, "name": name}
