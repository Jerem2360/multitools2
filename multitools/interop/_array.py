import ctypes
import struct
import sys

import _ctypes

from .._meta import generic
from ._base_type import CTypeMeta, CType
from ..errors._errors import err_depth, TYPE_ERR_STR
from ._mem import Memory
from .._parser import parse_args
from ..interface import SupportsIndex


class ArrayType(CTypeMeta):
    @property
    def __simple__(cls):
        return cls.__atype__.__simple__ * cls.__length__

    def __repr__(cls):
        return f"<C type '{cls.__atype__.__name__}[{cls.__length__}]'>"


@generic(CTypeMeta, SupportsIndex)  # Array[type: type[CType], len: SupportsIndex]
class Array(CType, metaclass=ArrayType):
    __atype__ = None
    __length__ = 0

    def __init__(self, *values):
        if type(self).__atype__ is None:
            raise err_depth(TypeError, "Array must specify a data type through template arguments.", depth=1)

        if type(self).__atype__.__type__ == '*':
            res_bytes = b""
            for val in values:
                if isinstance(val, CType):
                    parse_args((val,), type(self).__atype__)
                    res_bytes += val.get_data()
                    continue

                try:
                    res_bytes += type(self).__atype__(val).get_data()
                except:
                    raise err_depth(sys.exc_info()[0], *sys.exc_info()[1].args, depth=1) from None

            self._data = Memory(len(res_bytes))
            self._data.view()[:] = res_bytes

            self._args = values
            return

        try:
            res_bytes = struct.pack(type(self).__atype__.__type__, *values)
        except struct.error:
            raise err_depth(TypeError, *sys.exc_info()[1].args, depth=1) from None
        self._data = Memory(len(res_bytes))
        self._data.view()[:] = res_bytes
        self._args = values

    @classmethod
    def __template__(cls, tp, length):
        res = cls.dup_shallow()
        res.__atype__ = tp
        res.__length__ = length.__index__()
        return res

    def __getitem__(self, item):
        parse_args((item,), SupportsIndex, depth=1)

        if item.__index__() < 0:  # support for reverse iteration
            item = type(self).__length__ + item.__index__()

        if item.__index__() >= type(self).__length__:
            raise err_depth(IndexError, "index out of range.", depth=1)

        itemsize = type(self).__atype__.__size__
        index = item.__index__() * itemsize
        buffer = self._data.view()[index:index+itemsize]
        res = type(self).__atype__.__new__(type(self).__atype__)
        res._data = Memory(buffer)
        return res

    def __setitem__(self, key, value):
        parse_args((key, value), SupportsIndex, CType, depth=1)

        if key.__index__() < 0:  # support for reverse iteration
            key = type(self).__length__ + key.__index__()

        if key.__index__() >= type(self).__length__:
            raise err_depth(IndexError, "index out of range.", depth=1)

        itemsize = type(self).__atype__.__size__
        index = key.__index__() * itemsize
        self._data.view()[index:index+itemsize] = bytes(value._data.view())

    def __delitem__(self, key):
        parse_args((key,), SupportsIndex, depth=1)

        if key.__index__() < 0:  # support for reverse iteration
            key = type(self).__length__ + key.__index__()

        if key.__index__() >= type(self).__length__:
            raise err_depth(IndexError, "index out of range.", depth=1)

        itemsize = type(self).__atype__.__size__
        index = key.__index__() * itemsize
        self._data.view()[index:index+itemsize] = b"\x00" * itemsize

    def __repr__(self):
        return f"<C struct[{type(self).__length__}] {type(self).__atype__}>"

