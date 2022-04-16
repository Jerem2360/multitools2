"""
Subpackage for importing functions from C.

'from multitools.external import *' provides the most important features of the C language.

Supports loading dlls via the import statement, as follows:

from multitools.dll import <dllname>

will load and import the dll <dllname>, adding automatically the correct
file extension depending on sys.platform.

C types are located in external.typedefs
"""
import ctypes as _ct

from ._library import ExternalFunction, Library
from ._pointer import Pointer
from ._array import Array
from . import _dllimport
from .._meta import MultiMeta as _Mt
from . import _c_types as typedefs
from .._typing import type_check as _tp_check


# private instance of msvcrt.dll:
_msvcrt = Library.load("msvcrt")


class _NullType(int, metaclass=_Mt):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, 0)

    def __init_subclass__(cls, **kwargs):
        raise TypeError("'_NullType' is not an acceptable base type.")

    def __repr__(self):
        return 'NULL'

    def __eq__(self, other):
        return other == 0

    @staticmethod
    def to_c():
        return _ct.c_int(0)


NULL = _NullType()  # considered as an int of value 0
"""The NULL constant of the C language."""


class _nullptr_t(Pointer):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, 0)

    def __init_subclass__(cls, **kwargs):
        raise TypeError("'_nullptr_t' is not an acceptable base type.")

    def __class_getitem__(cls, item):
        raise NotImplementedError("Type '_nullptr_t' isn't subscriptable.")

    def __getitem__(self, item):
        raise NotImplementedError("'nullptr' isn't subscriptable.")

    def __setitem__(self, key, value):
        raise NotImplementedError("'nullptr' isn't subscriptable.")

    def __iter__(self):
        raise NotImplementedError("'nullptr' is not iterable.")

    def __repr__(self):
        return "nullptr"

    def __eq__(self, other):
        if isinstance(other, Pointer):
            return other == 0
        return False


# noinspection PyTypeChecker
nullptr = _nullptr_t()  # considered as a pointer to address 0.
"""NULL pointer"""


def GetLastError(hex_=True):
    _tp_check((hex_,), bool)
    return hex(_ct.GetLastError()) if hex_ else _ct.GetLastError()


def malloc(size):
    _tp_check((size,), int)
    _malloc = _msvcrt.reference("malloc", argtypes=(_ct.c_int,), restype=_ct.c_void_p)
    return Pointer(_malloc(_ct.c_int(size)).value)


def calloc(count, size):
    _tp_check((count, size), int, int)
    _calloc = _msvcrt.reference("calloc", argtypes=(_ct.c_int, _ct.c_int), restype=_ct.c_void_p)
    return Pointer(_calloc(_ct.c_int(count), _ct.c_int(size)).value)


"""def free(ptr):
    _tp_check((ptr,), Pointer)
    _free = _msvcrt.reference("free", argtypes=(_ct.c_void_p,), restype=None)
    _free(_ct.c_void_p(ptr))
"""  # doesn't work: memory corruption


def realloc(ptr, size):
    _tp_check((ptr, size), Pointer, int)
    _realloc = _msvcrt.reference("realloc", argtypes=(_ct.c_void_p, _ct.c_int), restype=_ct.c_void_p)
    return Pointer(_realloc(_ct.c_void_p(ptr.__address__), _ct.c_int(size)).value)


def sizeof(obj):
    if hasattr(obj, '__size__'):
        return obj.__size__
    if hasattr(obj, '__int__'):
        return int(obj).bit_length()
    if hasattr(obj, '__float__'):
        return float(obj).as_integer_ratio()[0].bit_length() + float(obj).as_integer_ratio()[1].bit_length()
    return _ct.sizeof(_ct.py_object(obj))


def DllImport(name, funcflags=0, libflags=0):
    _tp_check((name, funcflags, libflags), str, int, int)
    return _dllimport.DllImport(name, funcflags=funcflags, libflags=libflags)

