import sys
import threading as _th


__all__ = [
    "register",
    "__terminate__",
    "terminate",
]


_hooks = []
_th_shutdown = _th._shutdown


def register(hook):
    """
    Register a callable to be a terminate hook.
    It will behave similar to std::terminate_hook in C++.
    It is also called upon normal termination.
    """
    _hooks.append(hook)


def __terminate__(hooks):
    """
    Original terminate function. Don't touch.
    """
    for hook in reversed(hooks):
        try:
            hook()
        except:
            print(f"Exception raised in terminate hook {hook}:", file=sys.stderr)
            sys.excepthook(*sys.exc_info())
    _th_shutdown()


terminate = __terminate__
"""
Function that calls all terminate hooks from the list, just before the interpreter exits.
Similar to atexit, except that hooks are called even on interrupts and exceptions.
"""


_th._shutdown = lambda: terminate(_hooks)

