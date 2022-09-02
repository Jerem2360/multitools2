# version 1.0.9 of library multitools2

"""
Multitools2 is a python library offering various system-related classes and functions.
For documentation, see the Wiki at https://github.com/Jerem2360/multitools2/wiki.
"""


__all__ = [
    "_LIB_NAME",
    "_LIB_PATH",
    "_ROOT_PATH",

    "_MS_WIN32",
    "_ANDROID",

    "_DEFAULT_ENCODING",
    "_DEFAULT_BYTEORDER",

    "_DLLFILE",
    "_EXEFILE",

    "_NOOP",
    "_NUL_B",

    "_debug",
]


import sys


### -------- Constants -------- ###


# library data:
_LIB_NAME = __name__
_LIB_PATH = __file__.removesuffix('\\__init__.py')

# root module data:
_ROOT_PATH = __file__

# platform-related constants:
_MS_WIN32 = sys.platform == "win32"
_ANDROID = hasattr(sys, 'getandroidapilevel')

# msvc environment details:
_DEFAULT_ENCODING = sys.getdefaultencoding()
_DEFAULT_BYTEORDER = sys.byteorder

# file system info:
_DLLFILE = '.dll' if _MS_WIN32 else '.so'
_EXEFILE = '.exe' if _MS_WIN32 else '.db'

# utility constants:
_NOOP = lambda *args,  **kwargs: None
_NOOP.__name__ = 'no_op'
_NOOP.__qualname__ = _LIB_NAME + '.no_op'
_NOOP.__module__ = _LIB_NAME
_NUL_B = b'\x00'


### -------- Stuff to do when loading the library -------- ###

# load importers:
from ._startup import _importers

# debug machinery:
from ._startup import _debug as _deb

def _debug(channel: str | None = None):
    """
    Enable debugging of the library.
    """
    _deb.__do_debug__ = True
    if channel not in _deb.__debug_channels__:
        _deb.__debug_channels__.append(channel)


# onexit machinery:
from ._startup import _onexit


