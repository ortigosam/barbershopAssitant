class DomainError(Exception):
    """Base exception for business/domain errors."""


class ClientNotFoundError(DomainError):
    """Raised when a client does not exist."""


class ClientAlreadyExistsError(DomainError):
    """Raised when a client already exists."""


class BookingAlreadyExistsError(DomainError):
    """Raised when a booking already exists."""


class BookingNotFoundError(DomainError):
    """Raised when a booking does not exist."""


class BookingOutsideBusinessHoursError(DomainError):
    """Raised when a booking is not within a bookable appointment slot."""
