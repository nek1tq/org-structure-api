class DomainError(Exception):
    """Base class for domain-level errors translated to HTTP responses."""


class NotFoundError(DomainError):
    """Resource not found (HTTP 404)."""


class ConflictError(DomainError):
    """Business rule violation: duplicate name, cycle, dependent records (HTTP 409)."""


class ValidationError(DomainError):
    """Invalid input that passed schema validation but failed business rules (HTTP 400)."""
