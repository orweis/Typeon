"""Check a module and re-execute it in place ("fuse"), as done by ``typeon.compile()``."""

import builtins
import os
import sys
import threading

from . import exceptions as typeonExceptions
from . import scanner

_state = threading.local()


def checkSource(source, filename="<string>"):
    """Scan ``source`` without executing it; return its AST.

    Raises ``TypeonException`` listing every problem found.
    """
    return scanner.TypeonTyper().handleModuleSource(source, filename)


def _fixModuleNames(namespace, tempName, realName):
    """Point functions/classes created under a temporary ``__name__`` back at the module."""
    seen = set()
    stack = list(namespace.values())
    while stack:
        obj = stack.pop()
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        # Unwrap staticmethod/classmethod and property accessors.
        for attr in ("__func__", "fget", "fset", "fdel"):
            inner = getattr(obj, attr, None)
            if inner is not None and isinstance(obj, (staticmethod, classmethod, property)):
                stack.append(inner)
        if getattr(obj, "__module__", None) == tempName and callable(obj):
            try:
                obj.__module__ = realName
            except (AttributeError, TypeError):
                continue
            if isinstance(obj, type):
                stack.extend(vars(obj).values())


def fuseCaller(frame):
    """Check the module that owns ``frame`` and re-run its code in that module's namespace.

    This executes the module's top-level code a second time; see the README.
    A ``compile()`` call made by a module that is itself being re-executed (the call at
    the end of that module) is ignored; other modules first imported during the re-run
    are checked normally.
    """
    moduleGlobals = frame.f_globals
    fusing = _state.__dict__.setdefault("fusing", set())
    if id(moduleGlobals) in fusing:
        return
    moduleName = moduleGlobals.get("__name__")
    path = moduleGlobals.get("__file__")
    module = sys.modules.get(moduleName)
    if module is None or module.__dict__ is not moduleGlobals:
        raise ImportError("Caller %r is not an imported module" % (moduleName,))
    if not path or not path.endswith(".py") or not os.path.isfile(path):
        raise ImportError(
            "Module %r was not loaded from a .py source file: %r" % (moduleName, path)
        )

    with open(path, "rb") as source:
        data = source.read()
    tree = checkSource(data, path)
    code = builtins.compile(tree, path, "exec")

    # Never let a __main__ guard fire during the re-execution.
    execName = "_typeon_fused_" + moduleName if moduleName == "__main__" else moduleName
    fusing.add(id(moduleGlobals))
    moduleGlobals["__name__"] = execName
    try:
        exec(code, moduleGlobals)
    finally:
        moduleGlobals["__name__"] = moduleName
        fusing.discard(id(moduleGlobals))
    if execName != moduleName:
        _fixModuleNames(moduleGlobals, execName, moduleName)


__all__ = ["checkSource", "fuseCaller", "typeonExceptions"]
