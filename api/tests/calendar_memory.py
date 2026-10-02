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
            yield self
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

    def move(self, identifier, timestamp):
        old = self.bookings[identifier]
        self.bookings[identifier] = Appointment(
            identifier, timestamp, old.telephone, old.name
        )
        return self.bookings[identifier]

    def delete(self, identifier):
        self.bookings.pop(identifier)
        for receipt in self.receipts.values():
            if identifier in receipt["ids"]:
                receipt.update(ids=[], invalidated=True)

    def receipt(self, key):
        return self.receipts.get(key)

    def save_receipt(self, key, fingerprint, ids):
        self.receipts[key] = dict(fingerprint=fingerprint, ids=ids, invalidated=False)
