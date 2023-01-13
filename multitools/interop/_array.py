import ctypes
import struct
import sys

import _ctypes
from ctypes import c_void_p as _void_p, c_char_p as _char_p, \
    c_wchar_p as _wchar_p

from .. import *
from .._meta import generic
from ._base_type import CTypeMeta, CType, NULL as _NULL
from ..errors._errors import err_depth, TYPE_ERR_STR, ATTR_ERR_STR
from ._mem import Memory
from .._parser import parse_args
from ..interface import SupportsIndex


class _ArrayIterator:
    def __init__(self, instance):
        self._instance = instance
        self._index = 0

    def __next__(self):
        try:
            res = self._instance[self._index]
        except IndexError or KeyError:
            raise StopIteration from None
        self._index += 1
        return res

    def __getattr__(self, item):
        if hasattr(self._instance, item):
            return getattr(self._instance, item)
        raise err_depth(AttributeError, ATTR_ERR_STR.format(type(self._instance).__name__, item), depth=1)


class ArrayType(CTypeMeta):
    @property
    def __simple__(cls):
        return ctypes.POINTER(cls.__atype__.__simple__)  # arrays are actually pointers

    def __repr__(cls):
        atype = cls.__atype__.__name__ + f'()[{cls.__length__}]' if cls.__atype__ is not None else 'Array'
        return f"<C type '{atype}'>"


@generic(CTypeMeta, SupportsIndex)  # Array[type: type[CType], len: SupportsIndex]
class Array(CType, metaclass=ArrayType):
    """
    Type representing C arrays.
    Array[T, n] represents an array of n elements of type T.
    """
    __type__ = 'P'
    __atype__ = None
    __length__ = 0

    def __init__(self, *values, auto_free=False):
        """
        Build and allocate a new C array.
        By default, an array's memory is not freed
        automatically, to allow C functions to manipulate
        them without having to keep a reference to a python
        object.
        To enable automatic freeing, pass auto_free=True as
        a parameter to the constructor.
        """
        if type(self).__atype__ is None:
            raise err_depth(TypeError, "Array must specify a data type and a size through template arguments.", depth=1)

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
            res_bytes += b"\x00"

            self._data = Memory(len(res_bytes))
            self._data.view()[:] = res_bytes

            self._args = values
            return

        try:
            to_pack = tuple((bytes(value._data) for value in values))
            res_bytes = struct.pack(type(self).__atype__.__type__ * type(self).__length__, *to_pack)
        except struct.error:
            raise err_depth(TypeError, *sys.exc_info()[1].args, depth=1) from None
        self._contents = Memory(len(res_bytes), auto_free=auto_free)  # allocate new memory; similar to PyMem_Malloc()
        self._contents[:] = res_bytes
        self._data = Memory(8)  # store the address of the allocated memory
        self._data[:] = self._contents.address.to_bytes(8, _DEFAULT_BYTEORDER, signed=False)
        self._args = values
        self._do_free = auto_free

    @classmethod
    def __template__(cls, tp, length):
        """
        Implement cls[tp, length]
        """
        parse_args((tp, length), type, SupportsIndex, depth=1)
        res = cls.dup_shallow()
        res.__atype__ = tp
        res.__length__ = length.__index__()
        return res

    def __getitem__(self, item):
        """
        Implement self[item]
        """
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
        """
        Implement self[key] = value
        """
        parse_args((key, value), SupportsIndex, CType, depth=1)

        if key.__index__() < 0:  # support for reverse iteration
            key = type(self).__length__ + key.__index__()

        if key.__index__() >= type(self).__length__:
            raise err_depth(IndexError, "index out of range.", depth=1)

        itemsize = type(self).__atype__.__size__
        index = key.__index__() * itemsize
        self._data.view()[index:index+itemsize] = bytes(value._data.view())

    def __delitem__(self, key):
        """
        Implement del self[item]
        Note that this replaces the corresponding memory
        with NUL bytes.
        """
        parse_args((key,), SupportsIndex, depth=1)

        if key.__index__() < 0:  # support for reverse iteration
            key = type(self).__length__ + key.__index__()

        if key.__index__() >= type(self).__length__:
            raise err_depth(IndexError, "index out of range.", depth=1)

        itemsize = type(self).__atype__.__size__
        index = key.__index__() * itemsize
        self._data.view()[index:index+itemsize] = b"\x00" * itemsize

    def __iter__(self):
        return _ArrayIterator(self)

    def __eq__(self, other):
        """
        Implement self == other
        Allow comparison with NULL
        """
        if (other is _NULL) and (self._addr == 0):
            return True
        return super().__eq__(other)

    def __to_ctypes__(self):
        """
        Convert this instance to its ctypes homologous.
        """
        _at = _ctypes.POINTER(type(self).__atype__.__simple__)
        # print(int(self))
        # print(_at, type(self).__atype__.__simple__)
        return ctypes.cast(int(self), type(self).__simple__)

    @classmethod
    def __from_ctypes__(cls, *values):
        """
        Create a new instance using a ctypes homologous
        This does not allocate new memory.
        """
        if cls.__atype__ is None:
            raise err_depth(TypeError, "Array must specify a data type and a size through template arguments.", depth=1)

        ob = values[0]
        parse_args((ob,), (int, _void_p, _char_p, _wchar_p, _ctypes._Pointer, _ctypes.Array))
        addr = (ctypes.cast(ob, _void_p) if not isinstance(ob, _void_p) else ob)
        res = cls.__new__(cls)

        res._data = Memory(memoryview(addr))
        res._args = (values[0],)
        res._contents = None
        res._do_free = False
        return res

    def __int__(self):
        """
        Implement int(self)
        This is the actual memory address where the contents are stored.
        """
        return int.from_bytes(self._data.view()[:], _DEFAULT_BYTEORDER)

    def __repr__(self):
        """
        Implement repr(self)
        """
        return f"<C struct {type(self).__atype__.__name__} [{type(self).__length__}]>"

    def free(self):
        """
        Free the memory associated with the C array.
        """
        try:
            self._contents.release()
        except:
            pass

    def __del__(self):
        """
        Destructor.
        Frees the array if needed.
        """
        try:
            if not self._do_free:
                return
        except:
            return
        self.free()

