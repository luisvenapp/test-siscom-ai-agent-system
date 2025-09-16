from typing import Any

"""
Global FastAPI exception and warning classes.
"""


class ImproperlyConfigured(Exception):
    """
    Raised when FastAPI is not configured correctly.
    """

    def __init__(self, message: str) -> None:
        """
        Initialize with a configuration error message.

        Args:
            message: Description of the misconfiguration.
        """
        super().__init__(message)
        self.message = message


class SuspiciousOperation(Exception):
    """
    Raised when a user performs a suspicious operation.
    """
    pass


class SuspiciousMultipartForm(SuspiciousOperation):
    """
    Raised for suspect MIME requests in multipart form data.
    """
    pass


class SuspiciousFileOperation(SuspiciousOperation):
    """
    Raised when a suspicious filesystem operation is attempted.
    """
    pass


class FastAPIUnicodeDecodeError(UnicodeDecodeError):
    """
    UnicodeDecodeError that includes the object causing the error.
    """

    def __init__(self, obj: Any, *args: Any) -> None:
        """
        Initialize with the object that failed to decode.

        Args:
            obj: The object passed to decoding.
            *args: Arguments for the base UnicodeDecodeError.
        """
        self.obj = obj
        super().__init__(*args)

    def __str__(self) -> str:
        """
        Return a detailed error message including the object and its type.
        """
        original = super().__str__()
        return (
            f"{original}. You passed in {self.obj!r} ({type(self.obj)})"
        )


class RequestValidationError(Exception):
    """
    Raised when request validation fails for a specific field.
    """

    def __init__(self, field: str, detail: str) -> None:
        """
        Initialize with field name and error detail.

        Args:
            field: Name of the invalid field.
            detail: Description of the validation error.
        """
        super().__init__(field, detail)
        self.field = field
        self.detail = detail

    def __str__(self) -> str:
        """
        Return a formatted validation error message.
        """
        return f"RequestValidationError: {self.field}: {self.detail}"
