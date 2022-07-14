import _thread
import os

from ._const import *

import _io


def defined(name):
    """
    Return whether a name of named path is defined in the global scope.
    Will trigger __getattr__() methods of all parent objects of the target.
    Private members are not searched.
    Does not support subscription.
    """
    loc = locals().copy()  # in case another thread changes them in between
    glob = globals().copy()
    try:
        del loc['loc']
        del glob['loc']
        del glob['glob']
    except:
        pass

    path = name.split('.')
    root = path[0]

    if root in glob:
        path_iter = glob[root]
    elif root in loc:
        path_iter = loc[root]
    else:
        return False

    path.pop(0)
    for node in path:
        if node not in dir(path_iter):
            return False
        path_iter = getattr(path_iter, node)
    return True


def customPath(value):
    def _wrap(x):
        x.__module__ = value
        return x
    return _wrap


def noPath(func):
    return customPath("builtins")(func)


def customName(name):
    def _wrap(x):
        x.__name__ = name
        x.__qualname__ = name
        return x
    return _wrap


class Synchronizer:
    """
    Primitives that allow thread-safe code execution by disallowing
    multiple of their executions to run at the same time.
    """
    def __init__(self, timeout=-1):
        self._lock = _thread.allocate_lock()
        self._timeout = timeout

    def __enter__(self):
        self._lock.acquire(blocking=True, timeout=self._timeout)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()


def nullbytes(size):
    res = b''
    for i in range(size):
        res += b'\x00'
    return res

