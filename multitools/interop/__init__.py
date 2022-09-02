"""
This submodule adds support for interoperating between python
and C / C++. It is similar to the ctypes module, except it
aims to make the use of this functionality as comfortable
and easy as possible for the user.

Note:
    Part of this module uses functionality from the ctypes module,
    so congrats to the ctypes team for all this awesome work.
"""

__all__ = [

]

from .._startup._debug import debugger

DEBUGGER = debugger("INTEROP/debug")


from . import _base_type

# to do export elements


del debugger


def __finalize__():
    ...
