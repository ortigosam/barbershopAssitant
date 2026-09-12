from psycopg_pool import ConnectionPool

from src.config import settings


pool = ConnectionPool(
    conninfo=(
        f"host={settings.postgres_host} "
        f"port={settings.postgres_port} "
        f"dbname={settings.postgres_db} "
        f"user={settings.postgres_user} "
        f"password={settings.postgres_password}"
    ),
)