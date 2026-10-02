"""Injectable clock for local Europe/Madrid wall-clock storage."""

from datetime import datetime
from zoneinfo import ZoneInfo


def madrid_now() -> datetime:
    return datetime.now(ZoneInfo("Europe/Madrid")).replace(tzinfo=None)
