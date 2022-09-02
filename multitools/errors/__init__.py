"""
Custom errors for the library.
"""

__all__ = [
    "AdvancedException",
    "ThreadError",
    "ProcessError",
    "ProcessModelError",
    "UnknownProcessError",
    "ProcessActivityError",
    "UnresolvedExternalError",
    "err_depth",
]

from .._startup._debug import debugger

DEBUGGER = debugger("ERRORS/debug")
del debugger


import sys
from . import _errors


AdvancedException = _errors.AdvancedException
ThreadError = _errors.ThreadError
ProcessError = _errors.ProcessError
ProcessModelError = _errors.ProcessModelError
UnknownProcessError = _errors.UnknownProcessError
ProcessActivityError = _errors.ProcessActivityError
UnresolvedExternalError = _errors.UnresolvedExternalError


def err_depth(etype, *args, depth=0, **kwargs):
    return _errors.err_depth(etype, *args, depth=depth+1, **kwargs)


def __finalize__():
    ...
