"""Typeon exceptions."""


class TypeonException(Exception):
    """Base class for all errors reported by Typeon.

    ``errors`` holds the individual findings (as strings) when the exception
    was raised by a scan; it is empty otherwise.
    """

    def __init__(self, message="", errors=None):
        super().__init__(message)
        self.errors = list(errors or [])


class TypeonNameError(TypeonException):
    """A name was used but never defined."""
