"""Compatibility module for the former combined PostgreSQL repository.

New code uses :class:`PostgresUnitOfWork` and focused repositories.
"""

from src.repositories.unit_of_work import PostgresTransaction, PostgresUnitOfWork

PostgresBarbershopStore = PostgresUnitOfWork
PostgresCalendarStore = PostgresUnitOfWork
Transaction = PostgresTransaction

__all__ = [
    "PostgresBarbershopStore",
    "PostgresCalendarStore",
    "PostgresTransaction",
    "PostgresUnitOfWork",
    "Transaction",
]
