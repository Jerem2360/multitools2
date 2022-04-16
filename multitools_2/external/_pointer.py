import ctypes as _ct

from .._meta import MultiMeta as _Mt
from .._errors import *
from .._typing import type_check as _tp_check
from ._c_types import CType as _Ct
from ._decorators import dllimport as _dllimport


__all__ = [
    "Pointer",
]


_ptr_types = {}


@_dllimport("msvcrt")
def malloc(size: _ct.c_int) -> _ct.c_void_p: ...


class Pointer(metaclass=_Mt):
    __type__ = None
    __size__ = _ct.sizeof(_ct.c_void_p)

    @classmethod
    def allocate(cls, size=_ct.sizeof(_ct.c_int)):
        """
        Allocate space into memory and return a pointer to it.

        For Pointer[None], allocate 'size' bytes of memory which defaults
        to the size of an int.
        For Pointer[type], always allocate sizeof(type) bytes of memory.
        """
        size = cls.__type__.__size__ if cls.__type__ is not None else size
        ptr = malloc(_ct.c_int(size))
        res = Pointer[cls.__type__](ptr)
        return res

    @classmethod
    def addressof(cls, obj):
        """
        Create and return a pointer that points to obj's address in memory.
        """
        if cls.__type__ is None:
            _tp_check((type(obj),), _Ct)
            return Pointer(_ct.addressof(obj.__handle__))
        _tp_check((obj,), cls.__type__)
        return Pointer[cls.__type__](_ct.addressof(obj.__handle__))

    def __new__(cls, address, *args, **kwargs):
        """
        Create and return a new Pointer[type] pointing to address.
        """
        _tp_check((address,), int)
        self = super().__new__(cls)
        self.__address__ = address
        return self

    def dereference(self):
        """
        Get the data the pointer points to, convert it to the pointer's type and return it.
        """
        if self.__type__ is None:
            raise TypeError("'void*' cannot be dereferenced.")
        ptr = _ct.cast(self.__address__, _ct.POINTER(self.__type__.__c_base__))
        return self.__type__.from_c(ptr[0])

    def __class_getitem__(cls, item):
        _tp_check((item,), (_Ct, None))
        if item in _ptr_types:
            return _ptr_types[item]
        res = cls
        res.__type__ = item
        _ptr_types[item] = res
        return res

    @classmethod
    def from_c(cls, ptr):
        try:
            val = _ct.cast(ptr, _ct.c_void_p)
        except:
            raise TypeError("Expected a pointer-like object.")

        return Pointer[cls.__type__](val.value)

    def to_c(self):
        if self.__type__ is None:
            return _ct.cast(self.__address__, _ct.c_void_p)

        return _ct.cast(self.__address__, _ct.POINTER(self.__type__.__c_base__))


_ptr_types[None] = Pointer

