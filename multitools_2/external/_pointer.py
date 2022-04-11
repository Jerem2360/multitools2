import ctypes
import _ctypes
from ctypes import util as _util

from .._meta import MultiMeta as _Mt
from .._typing import type_check as _tp_check
from ._c_types import CType as _Ct, Int as _Int


_CData = ctypes.c_int.__mro__[-2]

_malloc = ctypes.CDLL("msvcrt.dll").malloc
_malloc.argtypes = (ctypes.c_int,)
_malloc.restype = ctypes.c_void_p


class Pointer(int, metaclass=_Mt):
    __type__: _Ct | None = None
    __size__ = ctypes.sizeof(ctypes.c_int)

    def __new__(cls, value, *args, **kwargs):
        ## print("address:", value)
        self = super().__new__(cls, value)
        self._initialized = False
        return self

    @classmethod
    def allocate(cls, size):
        _tp_check((size,), int)
        return Pointer[cls.__type__](_malloc(ctypes.c_int(size)))

    @classmethod
    def addressof(cls, obj):
        if isinstance(obj, _CData):
            # noinspection PyTypeChecker
            return Pointer[cls.__type__](ctypes.addressof(obj))
        if isinstance(type(obj), _Ct):
            return Pointer[cls.__type__](ctypes.addressof(obj.to_c()))
        return Pointer(ctypes.addressof(obj))

    def deref(self):
        if self.__type__ is None:
            raise ValueError("Cannot dereference a pointer to an unknown type.")
        # noinspection PyTypeChecker
        std_ptr = ctypes.cast(self, ctypes.POINTER(self.__type__.__c_base__))
        if not self._initialized:
            # noinspection PyAttributeOutsideInit
            self._initialized = True
            return self.__type__.from_c(std_ptr.contents)
        return self.__type__(std_ptr[0])

    def __class_getitem__(cls, item):
        _tp_check((item,), (_Ct, None))
        res = cls
        res.__type__ = item
        return res

    def __repr__(self):
        tpname = 'void*'
        if self.__type__ is not None:
            tpname = self.__type__.base + '*' if isinstance(self.__type__, _Ct) else self.__type__.__name__ + '*'

        return f"<'{tpname}' pointer at {hex(id(self))}>"

    def __getitem__(self, item):  # Access Violation? hum...
        _tp_check((item,), int)
        ## print("self:", int(self))
        # noinspection PyTypeChecker
        std_p = ctypes.cast(self, ctypes.POINTER(self.__type__.__c_base__))
        ## print("ctypes.pointer at getitem:", ctypes.addressof(std_p.contents))
        return self.__type__(std_p[item])

    def __setitem__(self, key, value):
        _tp_check((key, value), int, lambda val: TypeError("'value' must be a C value.") if not isinstance(type(val), _Ct) else 0)
        # noinspection PyTypeChecker
        std_p = ctypes.cast(self, ctypes.POINTER(self.__type__.__c_base__))
        ## print("ctypes.pointer at setitem:", ctypes.addressof(std_p.contents))
        std_p[key] = value.to_c()

    def __iter__(self):
        iterator = self
        iterator._count = 0
        return iterator

    def __next__(self):
        if not hasattr(self, '_count'):
            raise StopIteration()
        if self.__type__ is None:
            size = 1
        else:
            size = self.__type__.__size__
        memaddr = self + (self._count * size)
        self._count += 1
        if Pointer[_Int](memaddr).deref() == 0:  # NULL
            raise StopIteration()
        return Pointer[self.__type__](memaddr).deref()

    def to_c(self):
        return self.__std__

    __std__ = property(lambda self: ctypes.cast(self, ctypes.POINTER(self.__type__.__c_base__)))

