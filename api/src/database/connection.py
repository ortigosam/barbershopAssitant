from typing import Any

from psycopg import Connection
from psycopg.conninfo import make_conninfo
from psycopg_pool import ConnectionPool

from src.config import settings

# Explicitly annotate `pool` to satisfy Pylance generic typing expectations.
# Use the psycopg `Connection` concrete type for the pool element type.
pool: ConnectionPool[Connection[Any]] = ConnectionPool(
    conninfo=make_conninfo(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    ),
    open=False,
)
