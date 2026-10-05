"""PostgreSQL adapter for customers, bookings and schedule configuration."""

from src.repositories.unit_of_work import PostgresUnitOfWork

PostgresBarbershopStore = PostgresUnitOfWork

__all__ = ["PostgresBarbershopStore"]
