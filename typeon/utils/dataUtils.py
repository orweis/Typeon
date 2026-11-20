"""Data helpers."""

import warnings
from collections.abc import Sequence


def flatten(collection, flattenStrings=False, **legacy):
    """Yield the leaf elements of ``collection`` and of all sequences nested in it.

    Strings and bytes are treated as leaves unless ``flattenStrings`` is true,
    in which case ``str`` values are split into characters (a one-character
    string is its own leaf, so the recursion always terminates).

    The pre-2.0 misspelled keyword ``flatenStrings`` is still accepted but
    deprecated.
    """
    if "flatenStrings" in legacy:
        warnings.warn(
            "'flatenStrings' is deprecated, use 'flattenStrings'",
            DeprecationWarning,
            stacklevel=2,
        )
        flattenStrings = legacy.pop("flatenStrings")
    if legacy:
        raise TypeError("unexpected keyword arguments: %s" % ", ".join(sorted(legacy)))
    for item in collection:
        if isinstance(item, (bytes, bytearray)) or not isinstance(item, Sequence):
            yield item
        elif isinstance(item, str):
            if flattenStrings and len(item) > 1:
                yield from flatten(item, flattenStrings)
            else:
                yield item
        else:
            yield from flatten(item, flattenStrings)


class GenericProxy:
    """A generic object proxy: wrap an object and access it seamlessly via the wrapper.

    Example::

        class SampleA(object):
            def __init__(self):
                self.a = 1
                self.b = 2

        class SampleARepr(GenericProxy):
            def __init__(self, target):
                self._proxyWrap(target)

            def __repr__(self):
                return "a==%s b==%s" % (self.a, self.b)

        >>> r = SampleARepr(SampleA())
        >>> r.a
        1
        >>> r
        a==1 b==2
    """

    _PROXY_ENABLED_INDICATOR = "_proxyEnabled"
    _PROXY_OWN_PROPS = "_ownProperties"

    def getWrappedObject(self):
        return self._proxyTarget

    def _proxyWrap(self, target, markProxyProperties=True):
        self._proxyTarget = target
        self._ownProperties = dir(self)
        if markProxyProperties:
            builtin = dir(object) + ["__dict__", "__weakref__"]
            for item in dir(target):
                if item not in builtin:
                    setattr(self, item, None)
        setattr(self, GenericProxy._PROXY_ENABLED_INDICATOR, True)

    def __getattribute__(self, name):
        try:
            # Is a target wrapped by the proxy (i.e. was _proxyWrap called)?
            object.__getattribute__(self, GenericProxy._PROXY_ENABLED_INDICATOR)
        except AttributeError:
            return object.__getattribute__(self, name)
        # Proxied: wrapper's own properties stay on the wrapper, the rest go to the target.
        if name not in object.__getattribute__(self, GenericProxy._PROXY_OWN_PROPS):
            return getattr(object.__getattribute__(self, "_proxyTarget"), name)
        return object.__getattribute__(self, name)
