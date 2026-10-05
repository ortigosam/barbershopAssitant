from contextlib import contextmanager
from copy import deepcopy

from src.domain.calendar import Appointment, Calendar


class MemoryStore:
    def __init__(self):
        windows = [("10:00", "14:00"), ("17:00", "21:00")]
        self.cal = Calendar(
            {
                i: (windows if i < 5 else [("10:00", "14:00")] if i == 5 else [])
                for i in range(7)
            },
            {},
        )
        self.version = 1
        self.clients = {}
        self.bookings = {}
        self.receipts = {}
        self.sequence = 0

    @contextmanager
    def transaction(self):
        snapshot = deepcopy(self.__dict__)
        try:
            yield MemoryTransaction(self)
        except Exception:
            self.__dict__ = snapshot
            raise

    def calendar(self):
        return self.cal, self.version

    def save_calendar(self, calendar):
        self.cal = calendar
        self.version += 1

    def customer(self, telephone):
        return self.clients.get(telephone)

    def save_customer(self, telephone, name):
        self.clients[telephone] = dict(telephone=telephone, name=name)
        return self.clients[telephone]

    def appointments(self, start, end, telephone=None):
        return sorted(
            [
                b
                for b in self.bookings.values()
                if b.timestamp < end
                and b.end > start
                and (telephone is None or b.telephone == telephone)
            ],
            key=lambda b: b.timestamp,
        )

    def appointment(self, identifier):
        return self.bookings.get(identifier)

    def insert(self, timestamp, telephone):
        self.sequence += 1
        value = Appointment(
            self.sequence, timestamp, telephone, self.clients[telephone]["name"]
        )
        self.bookings[value.id] = value
        return value

    def delete(self, identifier):
        self.bookings.pop(identifier)
        for receipt in self.receipts.values():
            if identifier in receipt["ids"]:
                receipt.update(ids=[], invalidated=True)

    def receipt(self, key):
        return self.receipts.get(key)

    def save_receipt(self, key, fingerprint, ids):
        self.receipts[key] = dict(fingerprint=fingerprint, ids=ids, invalidated=False)


class MemoryTransaction:
    """Small in-memory UnitOfWork adapter used by application tests."""

    def __init__(self, store):
        self.clients = MemoryClients(store)
        self.bookings = MemoryBookings(store)
        self.schedule = MemorySchedule(store)
        self.receipts = MemoryReceipts(store)


class MemoryClients:
    def __init__(self, store):
        self.store = store

    def get(self, telephone):
        return self.store.customer(telephone)

    def save(self, telephone, name):
        return self.store.save_customer(telephone, name)


class MemoryBookings:
    def __init__(self, store):
        self.store = store

    def list(self, start, end, telephone=None):
        return self.store.appointments(start, end, telephone)

    def get(self, identifier):
        return self.store.appointment(identifier)

    def create(self, timestamp, telephone):
        return self.store.insert(timestamp, telephone)

    def delete(self, identifier):
        self.store.bookings.pop(identifier)


class MemorySchedule:
    def __init__(self, store):
        self.store = store

    def get(self):
        return self.store.calendar()

    def save(self, calendar):
        return self.store.save_calendar(calendar)


class MemoryReceipts:
    def __init__(self, store):
        self.store = store

    def get(self, key):
        return self.store.receipt(key)

    def save(self, key, fingerprint, ids):
        return self.store.save_receipt(key, fingerprint, ids)

    def invalidate_for_booking(self, identifier):
        for receipt in self.store.receipts.values():
            if identifier in receipt["ids"]:
                receipt.update(ids=[], invalidated=True)
