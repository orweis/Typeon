"""Typeon: compile-time name and type checks for Python.

Usage::

    import typeon
    from typeon import var

    def scale(value=var(int, 1), factor=var(float, 2.0)):
        return value * factor

    typeon.compile()   # checks this module; raises TypeonException on errors

See the README for details and limitations.
"""

import sys

from ._fuse import checkSource, fuseCaller
from .exceptions import TypeonException, TypeonNameError

__version__ = "2.0.0"

__all__ = [
    "Typeon",
    "TypeonException",
    "TypeonNameError",
    "__version__",
    "checkFile",
    "checkSource",
    "compile",
    "var",
]


def var(typeClass=None, defaultValue=None):
    """Mark a parameter type: ``def f(x=var(int, 5))``. At runtime returns the default."""
    return defaultValue


def compile():
    """Check the calling module and re-execute it in place.

    Raises ``TypeonException`` if problems are found. This runs the calling
    module's top-level code a second time, so only use it on code you trust.
    Shadows the builtin ``compile`` inside this package namespace only.
    """
    fuseCaller(sys._getframe(1))


def checkFile(path):
    """Statically check the Python file at ``path`` without executing it."""
    with open(path, "rb") as source:
        return checkSource(source.read(), str(path))


class Typeon:
    """Namespace kept for backward compatibility: ``Typeon.compile()``."""

    compile = staticmethod(compile)
