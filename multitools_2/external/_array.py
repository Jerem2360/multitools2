import ctypes

from .._meta import MultiMeta as _Mt
from ._pointer import Pointer
from .._typing import type_check as _tp_check
from ._c_types import Int as _Int
            ## ------------------- Work in Progress! -----------------------  ##


class Array(metaclass=_Mt):
    __type__ = None
    __size__ = 0

    def __init__(self, *elements, size=None):
        if size is None:
            size = len(elements)
        self._length = size
        if self.__type__ is None:
            raise ValueError("C arrays must be of a specific type.")
        if size == 0:  # nullptr if a 0-length array
            self.__pointer__ = Pointer[self.__type__](0)
            return
        self.__pointer__ = Pointer[self.__type__].allocate(self.__type__.__size__)
        self.__pointer__.__std__.contents = ctypes.c_int(0)
        for i in range(size):
            try:
                self.__pointer__[i] = elements[i]
            except IndexError:
                self.__pointer__[i] = self.__type__(0)
        Pointer[_Int](self.__pointer__)[size] = _Int(0)  # NULL-terminated array

    def __getitem__(self, item):
        if (item >= self._length) or (self.__pointer__ == 0):  # nullptr
            raise IndexError(f"'Array[{self.__type__.__name__}]': index '{item}' out of range.")
        return self.__pointer__[item]

    def __setitem__(self, key, value):
        if (key >= self._length) or (self.__pointer__ == 0):  # nullptr
            raise IndexError(f"'Array[{self.__type__.__name__}]': index '{key}' out of range.")
        self.__pointer__[key] = value

    def __class_getitem__(cls, item):
        _tp_check((item,), type)
        res = cls
        res.__type__ = item
        return res

    def __len__(self):
        return self._length

    def __iter__(self):
        res = self
        res._iterator = 0
        return res

    def __next__(self):
        if not hasattr(self, '_iterator') or self._iterator >= self._length:
            raise StopIteration()
        res = self[self._iterator]
        self._iterator += 1
        return res

    def __repr__(self):
        res = ""
        for item in self:
            res += repr(item)
            res += ", "
        res = res.removesuffix(", ")
        return f"<Array[{self.__type__.__name__}] " + "{" + res + "}>"

    def to_c(self):
        items = (i for i in self)
        std_ArrType = self.__type__.__c_base__ * self._length
        return std_ArrType(*items)

    @classmethod
    def from_c(cls, cvalue):
        std_ptr = ctypes.cast(cvalue, ctypes.POINTER(cls.__type__.__c_base__))
        self = cls.__new__(cls)
        self.__pointer__ = Pointer[cls.__type__](ctypes.addressof(std_ptr.contents))
        self._length = len(cvalue)
        return self

