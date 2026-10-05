"""PostgreSQL adapter for customers, bookings and schedule configuration."""

from src.repositories.calendar_store import PostgresBarbershopStore

__all__ = ["PostgresBarbershopStore"]
