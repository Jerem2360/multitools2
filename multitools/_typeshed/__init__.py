"""
Provides runtime-compatible types with adequate stubs for existing opaque
types.
"""

__all__ = [
    "CData",
    "SimpleCData",
    "PyCSimpleType",
    "CArgObject",
    "Function",
    "Code",
    "Cell",
    "Method",
    "Module",
    "Traceback",
    "Frame",
    "MethodWrapper",
    "WrapperDescriptor",
]

import sys

import _ctypes
import ctypes

# opaque types from ctypes module:
# noinspection PyTypeChecker
CData = _ctypes._SimpleCData.__base__
SimpleCData = _ctypes._SimpleCData
# noinspection PyTypeChecker
PyCSimpleType = type(_ctypes._SimpleCData)
"""metatype for the PyCSimple (_SimpleCData) Objects."""
CArgObject = type(ctypes.c_ulong.from_param(10))


# function-related types:
def f(x):
    def _inner():
        return x

    return _inner


Function = type(f)
"""Create a function object."""
# noinspection PyTypeChecker
Code = type(f.__code__)
"""Create a code object.  Not for the faint of heart."""
Cell = type(f(10).__closure__[0])
"""
Create a new cell object.

    contents
      the contents of the cell. If not specified, the cell will be empty,
      and
    further attempts to access its cell_contents attribute will
      raise a ValueError.
"""
del f


# class-related types:
class C:
    def f(self): ...


Method = type(C().f)
"""Create a bound instance method object."""
del C

# module-related types:
Module = type(sys)
"""
Create a module object.
The name must be a string; the optional doc argument can have any type.
"""

# runtime-related types:
exc_info = None, None, None
try:
    raise Exception
except:
    exc_info = sys.exc_info()

Traceback = type(exc_info[2])
"""Create a new traceback object."""
# noinspection PyTypeChecker
Frame = type(exc_info[2].tb_frame)

del exc_info

MethodWrapper = type((10).__index__)

WrapperDescriptor = type(int.__index__)

