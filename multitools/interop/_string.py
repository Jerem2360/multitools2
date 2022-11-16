import ctypes

from ._base_type import CType, CTypeMeta
from ._array import Array
from ._chars import Char

from .. import *
from .._parser import parse_args
from ..errors._errors import err_depth, TYPE_ERR_STR
from ..interface import SupportsIndex


class String(CType, metaclass=CTypeMeta):
    __type__ = 'P'
    __simple__ = ctypes.c_char_p

    def __init__(self, data, /, *, auto_free=True):
        parse_args((data, auto_free), str, bool, depth=1)
        self._args = (bytes(c, encoding=_DEFAULT_ENCODING) for c in data)
        # print(tuple(self._args))
        arr = Array[Char, len(data) + 1](*tuple(self._args), b'\x00')
        self._ptr = int(arr)
        self._data = arr._data
        self._do_free = auto_free
        self._size = len(data)

    def __del__(self):
        if not self._do_free:
            return
        self.free()

    def free(self):
        self.array.free()

    @property
    def array(self):
        arr = Array[Char, self._size].__new__(Array[Char, self._size])
        print(self._size)
        arr._data = self._data
        arr._args = self._args
        return arr

    def __getitem__(self, item):
        parse_args((item,), SupportsIndex | slice, depth=1)
        if isinstance(item, SupportsIndex):
            index = item.__index__()
            return self.array.__getitem__(index)
        res = ""
        arr = self.array
        for i in range(item.start, item.stop, item.step):
            c = arr.__getitem__(i)
            _data = bytes(c._data)
            res += str(_data, encoding=_DEFAULT_ENCODING)

        return String(res, auto_free=self._do_free)

    def __setitem__(self, key, value):
        parse_args((key, value), SupportsIndex | slice, Char | String, depth=1)
        if isinstance(key, SupportsIndex):
            parse_args((value,), Char, depth=1)
            self.array.__setitem__(key, value)
            return

        if isinstance(value, Char):
            res = ""
            arr = self.array
            for i in range(key.start, key.stop, key.step):
                c = arr.__getitem__(i)
                _data = bytes(c._data)
                res += str(_data, encoding=_DEFAULT_ENCODING)
            value = String(res)
        data = value.array

        i = key.start
        for c in data:
            self.__setitem__(i, c)
            i += key.step

    def __delitem__(self, key):
        parse_args((key,), SupportsIndex | slice)
        self.array.__delitem__(key)

    @classmethod
    def __from_ctypes__(cls, *values):
        if len(values) <= 0:
            raise err_depth(TypeError, "C 'char*' expected at least one argument.", depth=1)
        if isinstance(values[0], int):
            value = ctypes.cast(values[0], ctypes.c_char_p)
        elif isinstance(values[0], ctypes.c_char_p):
            value = values[0]
        else:
            raise err_depth(TypeError, TYPE_ERR_STR.format(' C char*', type(values[0]).__name__), depth=1)

        res = cls(str(value.value, encoding=_DEFAULT_ENCODING))
        res._do_free = False
        return res

    def __to_ctypes__(self):
        # return ctypes.cast(self._data.address, ctypes.c_char_p)
        return self.array.__to_ctypes__()

