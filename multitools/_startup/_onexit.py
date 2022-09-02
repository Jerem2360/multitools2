"""
Support for scheduling the execution of functions to just before
the interpreter exits.
"""


__all__ = [
    "_register",
]


import sys
import threading

from . import _import_data


__hooks__ = {}


def _register(op, name):
    """
    Register a callable to the onexit hooks.
    """
    __hooks__[name] = op


_old_shutdown = threading._shutdown

def _shutdown():
    """
    We override threading._shutdown, which will get called just before the interpreter
    exits.
    """
    _old_shutdown()
    __hooks__.update(_import_data.__finalizers__)

    from .. import _LIB_NAME
    sys.audit(f"{_LIB_NAME}.onexit")
    for name, hook in __hooks__.items():
        try:
            sys.audit(f"{_LIB_NAME}.onexit.hook", name)
        except:
            continue

        try:
            hook()
        except:
            print(f"Exception raised in onexit hook '{name}':", file=sys.stderr)
            sys.excepthook(*sys.exc_info())


_shutdown.__qualname__ = _old_shutdown.__qualname__
_shutdown.__module__ = _old_shutdown.__module__
threading._shutdown = _shutdown

