import ctypes
import struct
import sys

from ._base_type import CType, CTypeMeta
from ._array import Array
from ._chars import Char, WChar
from ._mem import Memory

from .. import *
from .._parser import parse_args, POS_ARGCOUNT_ERR_STR
from ..errors._errors import err_depth, TYPE_ERR_STR
from ..interface import SupportsIndex


class String(CType, metaclass=CTypeMeta):
    __type__ = 'P'
    __simple__ = ctypes.POINTER(ctypes.c_char)

    def __init__(self, data, /, *, auto_free=True):
        parse_args((data, auto_free), str, bool, depth=1)
        bytes_ = tuple(bytes(c, encoding=_DEFAULT_ENCODING) for c in data)
        if bytes_[-1] != b'\x00':
            bytes_ = (*bytes_, b'\x00')
        try:
            packed = struct.pack('c'*len(bytes_), *bytes_)
        except struct.error as e:
            raise err_depth(TypeError, *e.args, depth=1) from None

        contents = Memory(len(packed), auto_free=False)
        contents[:] = packed
        packed_address = struct.pack('N', contents.address)
        self._data = Memory(len(packed_address), auto_free=False)
        self._data[:] = packed_address
        self._length = len(bytes_)
        self._args = (data,)
        self._do_free = auto_free
        self._ = contents

    def __del__(self):
        if not self._do_free:
            return
        self.free()

    def free(self):
        self._contents().release()
        self._data.release()

    def __getitem__(self, item):
        parse_args((item,), SupportsIndex | slice)
        view = self._contents().view()
        res = Char.__new__(Char)
        ind = item if isinstance(item, slice) else item.__index__()
        res._data = view[ind]
        return res

    def __setitem__(self, key, value):
        parse_args((key, value), SupportsIndex | slice, Char | bytes, depth=1)
        view = self._contents().view()
        data = bytes(value._data) if isinstance(value, Char) else (value if (isinstance(value, bytes) and (len(value) == 1)) else None)
        if data is None:
            raise err_depth(ValueError, "value must be a C char or a byte string of length 1.", depth=1)

        ind = key if isinstance(key, slice) else key.__index__()
        view[ind] = data

    def __delitem__(self, key):
        parse_args((key,), SupportsIndex | slice, depth=1)
        data = b'\x00'
        if isinstance(key, slice):
            data *= (key.stop - key.start) / key.step
        self.__setitem__(key, data)

    def _contents(self):
        address = int.from_bytes(bytes(self._data.view()), _DEFAULT_BYTEORDER, signed=False)
        temp = (ctypes.c_char * self._length).from_address(address)
        return Memory(memoryview(temp), auto_free=False)

    @classmethod
    def __from_ctypes__(cls, *values):
        if len(values) != 1:
            raise err_depth(TypeError, POS_ARGCOUNT_ERR_STR.format(f"{cls.__name__}.__from_ctypes__()", 1, len(values)))
        self = cls.__new__(cls)
        self._data = Memory(values[0], auto_free=False)
        self._length = len(values[0].value)
        self._args = (values[0].value,)
        self._do_free = False
        return self

    def __to_ctypes__(self):
        return ctypes.POINTER(ctypes.c_char).from_buffer(self._data.view())


class WString(CType, metaclass=CTypeMeta):
    __type__ = 'P'
    __simple__ = ctypes.POINTER(ctypes.c_wchar)

    def __init__(self, data, /, *, auto_free=True):
        parse_args((data, auto_free), str, bool, depth=1)
        packed = b""
        for char in data:
            wc = WChar(char)
            packed += wc._data[:]

        contents = Memory(len(packed), auto_free=False)
        contents[:] = packed
        packed_address = struct.pack('N', contents.address)
        self._data = Memory(len(packed_address), auto_free=False)
        self._data[:] = packed_address
        self._length = len(packed)
        self._args = (data,)
        self._do_free = auto_free
        self._ = contents

    def __del__(self):
        if not self._do_free:
            return
        self.free()

    def free(self):
        self._contents().release()
        self._data.release()

    def __getitem__(self, item):
        parse_args((item,), SupportsIndex | slice)
        view = self._contents().view()
        res = WChar.__new__(WChar)
        ind = item if isinstance(item, slice) else item.__index__()
        res._data = view[ind]
        return res

    def __setitem__(self, key, value):
        parse_args((key, value), SupportsIndex | slice, WChar | str, depth=1)
        view = self._contents().view()
        data = bytes(value._data) if isinstance(value, WChar) else (value if (isinstance(value, bytes) and (len(value) == 1)) else None)
        if data is None:
            raise err_depth(ValueError, "value must be a C char or a byte string of length 1.", depth=1)

        ind = key if isinstance(key, slice) else key.__index__()
        view[ind] = data

    def __delitem__(self, key):
        parse_args((key,), SupportsIndex | slice, depth=1)
        data = b'\x00'
        if isinstance(key, slice):
            data *= (key.stop - key.start) / key.step
        self.__setitem__(key, data)

    def _contents(self):
        address = int.from_bytes(bytes(self._data.view()), _DEFAULT_BYTEORDER, signed=False)
        temp = (ctypes.c_wchar * self._length).from_address(address)
        return Memory(memoryview(temp), auto_free=False)

    @classmethod
    def __from_ctypes__(cls, *values):
        if len(values) != 1:
            raise err_depth(TypeError, POS_ARGCOUNT_ERR_STR.format(f"{cls.__name__}.__from_ctypes__()", 1, len(values)))
        self = cls.__new__(cls)
        self._data = Memory(values[0], auto_free=False)
        self._length = len(values[0].value)
        self._args = (values[0].value,)
        self._do_free = False
        return self

    def __to_ctypes__(self):
        return ctypes.POINTER(ctypes.c_wchar).from_buffer(self._data.view())

