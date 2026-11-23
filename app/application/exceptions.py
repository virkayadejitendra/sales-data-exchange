class ApplicationError(Exception):
    """Base class for expected application errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ResourceNotFoundError(ApplicationError):
    """Raised when a requested resource does not exist."""


class ResourceConflictError(ApplicationError):
    """Raised when a uniqueness rule would be violated."""


class BusinessRuleError(ApplicationError):
    """Raised when a request violates a domain rule."""


class SalesValidationError(BusinessRuleError):
    """Raised when one or more sales rows fail business validation."""

    def __init__(self, message: str, errors: list[dict[str, object]]) -> None:
        super().__init__(message)
        self.errors = errors
