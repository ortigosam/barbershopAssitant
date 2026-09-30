from typing import Any, Optional, Tuple, LiteralString, cast

from psycopg import Connection
from psycopg_pool import ConnectionPool


ClientRow = Tuple[str, str]


class ClientRepository:

    def __init__(self, pool: ConnectionPool[Connection[Any]]):
        self.pool: ConnectionPool[Connection[Any]] = pool

    def get_by_telephone(self, telephone: str) -> Optional[ClientRow]:
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                qry: LiteralString = """
                SELECT telephone, name
                FROM client
                WHERE telephone = %s
                """
                cursor.execute(qry, (telephone,))

                return cast(Optional[ClientRow], cursor.fetchone())

    def create(self, telephone: str, name: str) -> ClientRow:
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                qry: LiteralString = """
                INSERT INTO client (telephone, name)
                VALUES (%s, %s)
                RETURNING telephone, name
                """
                cursor.execute(qry, (telephone, name))

                client = cast(Optional[ClientRow], cursor.fetchone())
                connection.commit()

                assert client is not None
                return client