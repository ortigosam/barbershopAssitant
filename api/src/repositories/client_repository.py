from psycopg_pool import ConnectionPool


class ClientRepository:

    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def get_by_telephone(self, telephone: str):
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT telephone, name
                    FROM client
                    WHERE telephone = %s
                    """,
                    (telephone,),
                )

                return cursor.fetchone()

    def create(self, telephone: str, name: str):
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO client (telephone, name)
                    VALUES (%s, %s)
                    RETURNING telephone, name
                    """,
                    (telephone, name),
                )

                client = cursor.fetchone()
                connection.commit()

                return client