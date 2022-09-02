import ctypes
import ctypes as _ct

from .._meta import *
from .._typeshed import *
from ..errors._errors import err_depth
from .._parser import *
from ..interface import Buffer, SupportsIndex


### -------- Constants -------- ###
__BASE_TYPE__ = '__base_type__'


def _slice_assign(mv_dest, start, stop, step, mv_source):
    n_dest = start
    n_source = 0

    while 1:
        mv_dest[n_dest] = mv_source[n_source]
        n_dest += step
        n_source += 1
        if (n_dest >= stop) or (n_source >= len(mv_source)):
            break


def _memoryview_from_memory(mv):
    """
    Internal helper using the C api to create a memoryview
    object of format 'B' exposing mv's data. If mv is deleted
    before the result of this function, reading will cause
    Access Violation.
    """
    ptr = _buffer_get_pointer(mv)
    size = mv.itemsize * len(mv)
    flags = 0x200

    c_res = ctypes.pythonapi.PyMemoryView_FromMemory(ctypes.c_void_p(ptr), ctypes.c_ssize_t(size), ctypes.c_int(flags))
    res = ctypes.cast(c_res, ctypes.py_object).value
    return res


def _buffer_get_pointer(buf):
    """
    Internal helper using the C api to fetch the pointer of a
    buffer object.
    """
    parse_args((buf,), Buffer, depth=1)

    class _Py_Buffer(ctypes.Structure):
        _fields_ = (
            ("buf", ctypes.c_void_p),
            ("obj", ctypes.c_void_p),
            ("len", ctypes.c_ssize_t),
            ("readonly", ctypes.c_int),
            ("itemsize", ctypes.c_ssize_t),
            ("format", ctypes.c_char_p),
            ("ndim", ctypes.c_int),
            ("shape", ctypes.c_void_p),
            ("strides", ctypes.c_void_p),
            ("suboffsets", ctypes.c_void_p),
            ("internal", ctypes.c_void_p),
        )

    data = _Py_Buffer()
    ctypes.pythonapi.PyObject_GetBuffer(ctypes.py_object(buf), ctypes.byref(data), ctypes.c_int(0))
    pointer = ctypes.c_ssize_t.from_address(ctypes.addressof(data)).value
    ctypes.pythonapi.PyBuffer_Release(ctypes.byref(data))
    return pointer


class _MemoryBuffer(metaclass=MultiMeta):
    """
    Mutable memory with a fixed size.
    """
    def __init__(self, *args, **kwargs):
        """
        Allocate a new memory block.
        MemoryBuffer(size: int) -> new memory block of the given size, filled with zeros
        MemoryBuffer(source: Buffer) -> new memory block, copying data from source
        """
        self._data = bytearray(*args, **kwargs)
        self._ndim = 1

    def __repr__(self):
        """
        Implement repr(self)
        """
        return f"({' '.join(hex(i) for i in self._data)})"

    def __bytes__(self):
        """
        Implement bytes(self)
        """
        return bytes(self._data)

    def __iter__(self):
        """
        Implement iter(self)
        """
        self._iterno = 0
        return self

    def __next__(self):
        """
        Implement next(self)
        """
        if self._iterno >= len(self._data):
            raise StopIteration
        res = self._data[self._iterno]
        self._iterno += 1
        return res

    def __len__(self):
        """
        Implement len(self)
        Return the length in bytes of the memory block.
        """
        return len(self._data)

    def __getitem__(self, item):
        """
        Implement self[item]
        """
        if isinstance(item, slice):
            start = item.start if item.start is not None else 0
            stop = item.stop if item.stop is not None else len(self)
            step = item.step if item.step is not None else 1

            return _MemoryBuffer(self.get_memory()[start:stop:step])

        parse_args((item,), SupportsIndex, depth=1)
        return self.get_memory()[item.__index__()]

    def __setitem__(self, key, value):
        """
        Implement self[key] = value
        """
        if isinstance(key, slice):

            parse_args((value,), Buffer, depth=1)
            start = key.start if key.start is not None else 0
            stop = key.stop if key.stop is not None else len(self)
            step = key.step if key.step is not None else 1

            if self._ndim != 1:
                # memoryview does not support slice assign for 0-dimensional memory.
                return _slice_assign(self.get_memory(), start, stop, step, memoryview(value))

            mv = memoryview(value)
            if len(mv) != ((stop / step) - start):
                raise err_depth(ValueError, "Data length is different from slice length.", depth=1)
            self.get_memory()[start:stop:step] = mv
            return

        parse_args((key, value), SupportsIndex, int, depth=1)
        if value >= 256:
            raise err_depth(OverflowError, "Value too big to be represented by a single byte. Limit is 255.", depth=1)
        self.get_memory()[key.__index__()] = value

    def __delitem__(self, key):
        """
        Implement del self[key]
        """
        if isinstance(key, slice):
            start = key.start if key.start is not None else 0
            stop = key.stop if key.stop is not None else len(self)
            step = key.step if key.step is not None else 1

            self.get_memory()[start:stop:step] = b'\x00' * ((stop / step) - start)
            return

        parse_args((key,), SupportsIndex, depth=1)
        self.get_memory()[key] = 0

    def __contains__(self, item):
        """
        Implement item in self
        """
        parse_args((item,), int, depth=1)
        return item in (self._data if isinstance(self._data, bytearray) else self.get_memory())

    def get_memory(self):
        """
        Return a memory view of self.
        """
        if isinstance(self._data, memoryview):
            return self._data
        return memoryview(self._data)

    def free(self):
        """
        Free the allocated memory. This is done by the destructor.
        """
        return self.get_memory().release()

    @classmethod
    def from_view(cls, mv):
        """
        Return the memory buffer of the given memoryview object, which
        must be writeable.
        """
        parse_args((mv,), memoryview)
        if mv.readonly:
            raise err_depth(TypeError, "Read-only memoryview object.", depth=1)
        if (not mv.c_contiguous) or (mv.ndim not in (0, 1)):
            raise err_depth(TypeError, "A C contiguous 0 or 1-dimensional view is required.", depth=1)
        self = super().__new__(cls)
        self._data = mv
        self._ndim = mv.ndim
        return self

    @property
    def size(self):
        """
        Number of bytes allocated in memory.
        This includes the trailing NUL byte at the end of the
        memory block.
        """
        # noinspection PyUnresolvedReferences
        return self._data.__alloc__() if isinstance(self._data, bytearray) else (self.get_memory().nbytes + 1)

    @property
    def buffer(self):
        """
        A buffer pointing to the memory. Virtually, this can be any type of buffer.
        """
        return self._data

    @property
    def address(self):
        """
        The address of the beginning of the memory block.
        """
        return _buffer_get_pointer(self.get_memory())


class CTypeMeta(MultiMeta):
    """
    Common metatype for all C data types.
    """
    def __new__(mcs, name, bases, np, **kwargs):
        """
        Create and return a new C data type.
        """
        if __BASE_TYPE__ not in np:
            np[__BASE_TYPE__] = _ct.py_object  # base type defaults to ctypes.py_object

        cls = super().__new__(mcs, name, bases, np, **kwargs)
        return cls


class CType(metaclass=CTypeMeta):
    """
    Base class for all C data types.
    """
    def __new__(cls, *args, **kwargs):
        """
        Create and return new C data.
        """
        self = super().__new__(cls)
        return self

    def __init__(self, data, *args, **kwargs):
        """
        Initialize new C data, given the data in python form.
        """
        self._buffer = type(self).__base_type__(data, *args, **kwargs)

    @classmethod
    def from_buffer(cls, buf, offset=0):
        """
        Interpret a python buffer object as C data.
        The buffer must be writable.
        """
        parse_args((buf, offset), Buffer, int, depth=1)
        self = cls.__new__(cls)
        self._buffer = cls.__base_type__.from_buffer(buf, offset=offset)
        return self

    @classmethod
    def from_buffer_copy(cls, buf, offset=0):
        """
        Same as from_buffer(), except that the buffer's data
        is copied to a writeable buffer before the data is
        interpreted. This de-synchronizes the buffer and the
        C data object, allowing the buffer to be read-only.
        """
        parse_args((buf, offset), Buffer, int, depth=1)
        self = cls.__new__(cls)
        self._buffer = cls.__base_type__.from_buffer_copy(buf, offset=offset)
        return self

