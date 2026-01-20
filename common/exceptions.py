"""Domain-specific exceptions for the expense tracker core services."""

class ValidationError(ValueError):
    """Raised when provided data does not meet validation requirements."""


class RecordNotFoundError(LookupError):
    """Raised when an expense or income record cannot be located."""


class PersistenceError(IOError):
    """Raised when the persistence layer encounters unrecoverable issues."""
