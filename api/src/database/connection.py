from typing import Any

from psycopg import Connection
from psycopg_pool import ConnectionPool

from src.config import settings


# Explicitly annotate `pool` to satisfy Pylance generic typing expectations.
# Use the psycopg `Connection` concrete type for the pool element type.
pool: ConnectionPool[Connection[Any]] = ConnectionPool(
    conninfo=(
        f"host={settings.postgres_host} "
        f"port={settings.postgres_port} "
        f"dbname={settings.postgres_db} "
        f"user={settings.postgres_user} "
        f"password={settings.postgres_password}"
    ),
)