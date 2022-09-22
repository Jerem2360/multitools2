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
    "dllimport",
    "sizeof",
    "cast",
    "NULL",

    "Library",
    "__cdecl",
    "__stdcall",

    "Short",
    "UShort",
    "Int",
    "UInt",
    "Long",
    "ULong",
    "LongLong",
    "ULongLong",

    "Char",
    "WChar",
    "Byte",
    "UByte",

    "PyObject",

    "CFunction",

    "Int",
    "Pointer",
    "Size_t",
    "SSize_t",
]

import sys

from . import _chars, _pointer, _structure, _int_types, _float_types, _func, _pyapi
from .._tools import Decorator as _Decorator
from .. import _parser
from .. import _typeshed
from ..errors import _errors
from ._loaders import Library as _Library


from .._startup._debug import debugger

DEBUGGER = debugger("INTEROP/debug")


from . import _base_type

# to do export elements


del debugger


@_Decorator
def dllimport(fn, source, callconv=1):
    """
    Import a function from an external library, i.e. a .dll file on Windows or
    .so file on posix and macOS. This also works for executable files.

    source must be the library or executable from which the function
    must be loaded. This can either be an already loaded Library object,
    or the string path to the given file.

    callconv is the convention for reading data from the library or
    executable. It must be __cdecl or __stdcall.
    """
    if 'return' not in fn.__annotations__:
        raise _errors.err_depth(TypeError, "Missing return type in signature.", depth=1)
    _parser.parse_args((fn, source, callconv), _typeshed.Function, _Library | str, int)
    if isinstance(source, str):
        source = _Library.load(source)
    signature = fn.__annotations__
    restype = signature.pop('return', ...)
    argtypes = tuple(signature.values())

    return source.get_proc(fn.__name__, argtypes=argtypes, restype=restype)


def sizeof(op):
    """
    Return the size of a C data type or of a C instance.
    If op isn't one of those, return sys.getsizeof(op)
    """
    if not isinstance(op, (_base_type.CType, _base_type.CTypeMeta)):
        return sys.getsizeof(op)
    return op.__size__ if isinstance(op, _base_type.CType) else type(op).__size__


def cast(val, tp):
    """
    Cast a value to the given data type of the same size.
    If val and tp don't have the same size, TypeError is raised.
    """
    _parser.parse_args((val, tp), _base_type.CType, _base_type.CTypeMeta, depth=1)
    # noinspection PyUnresolvedReferences
    if type(val).__size__ != tp.__size__:
        raise _errors.err_depth(TypeError, "Cannot cast a value to a type of different size.", depth=1)

    inst = tp.__new__(tp)
    # noinspection PyUnresolvedReferences
    inst._data = val._data
    return inst


Library = _Library

CType = _base_type.CType

CFunction = _func.CFunction

Bool = _int_types.Bool

Short = _int_types.Short
UShort = _int_types.UShort
Int = _int_types.Int
UInt = _int_types.UInt
Long = _int_types.Long
ULong = _int_types.ULong
LongLong = _int_types.LongLong
ULongLong = _int_types.ULongLong
Size_t = _int_types.Size_t
SSize_t = _int_types.SSize_t

Float = _float_types.Float
Double = _float_types.Double
LongDouble = _float_types.LongDouble

Char = _chars.Char
WChar = _chars.WChar
Byte = _chars.Byte
UByte = _chars.UByte

Struct = _structure.Struct

PyObject = _pyapi.PyObject
PyTypeObject = _pyapi.PyTypeObject

Pointer = _pointer.Pointer

NULL = _base_type.NULL


__stdcall = _loaders.CallConv(0)
__cdecl = _loaders.CallConv(1)


def __finalize__():
    ...
