import mmap
import pickle

from . import _helpers
from ._const import *


EMPTY = pickle.dumps({})


if MS_WINDOWS:
    from ._win32 import shared_memory as _shared_memory, unmap as _unmap
else:
    from ._posix import shared_memory as _shared_memory, unmap as _unmap


"""class SharedMemory:
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._mmap = None
        self._buf = None
        self._name = ''
        self._size = 0
        if not MS_WINDOWS:
            self._fd = 0
        return self

    def __init__(self, name=None, create=False):
        *args, kwargs, mem_name = _shared_memory(name, len(EMPTY), create=create)
        self._mmap = mmap.mmap(*args, **kwargs)
        self._buf = memoryview(self._mmap)
        self._name = mem_name
        self._size = args[1]
        if not MS_WINDOWS:
            self._fd = args[0]
        
    def free(self):
        fd = self._fd if not MS_WINDOWS else -1
        _unmap(self._buf, self._mmap, fd)"""


"""class SharedMemory:
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._header = (None, None, None, None, None)
        self._data = (None, None, None, None, None)
        return self

    def __init__(self, size, name=None, create=False):
        self._header = self._sort_buffer(name, 14, create)
        self._header[3][:] = SHORT_TRUE + size.to_bytes(8, 'big', signed=False) + _data_id.to_bytes(4, 'big', signed=False)
        self._data = self._sort_buffer(None, -1, create)
    
    @staticmethod
    def _sort_buffer(name, size, create):
        *args, kwargs, name = _shared_memory(name, size, create=create)
        mmap_ = mmap.mmap(*args, **kwargs)
        buf_ = memoryview(mmap_)
        fd_ = -1 if MS_WINDOWS else args[0]
        size_ = args[1]
        return name, fd_, mmap_, buf_, size_"""


class SharedMemory:
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._header = [None, None, None, None, None]
        self._data = [None, None, None, None, None]
        return self

    def __init__(self, id_=None, create=False):
        self._data = self._sort_buffer(id_, 1, create)
        self._data[3][:] = b'\x00'
        # header format: uint16 locked; uint64 data_size; uint32 data_id;
        header_contents = SHORT_TRUE + self._data[4].to_bytes(8, 'big', signed=False) + \
                          self._data[0].to_bytes(4, 'big', signed=False)
        self._header = self._sort_buffer(id_, len(header_contents), create)
        self._header[3][:] = header_contents
        self._header[3][:2] = SHORT_FALSE

    def _update(self):
        size = bytes(self._header[3][2:10])
        id_ = bytes(self._header[3][10:])
        self._data = self._sort_buffer(id_, size, False)

    def _resize(self, new_size):
        self._update()
        locked_before = bytes(self._header[3][:2])
        self._header[3][:2] = SHORT_TRUE
        data = bytes(self._data[3][:])
        _unmap(self._data[3], self._data[2], self._data[1])
        self._data = self._sort_buffer(None, new_size, True)
        header_contents = SHORT_TRUE + new_size.to_bytes(8, 'big', signed=False) + \
            self._data[0].to_bytes(4, 'big', signed=False)
        self._header[3][:] = header_contents
        self._data[3][:] = _helpers.match_length(data, new_size)
        self._header[3][:2] = locked_before

    @staticmethod
    def _sort_buffer(id_, size, create):
        """
        Format:
        (id: int, fd: int, mmap: mmap.mmap, buf: memoryview, size: int)
        """
        *args, kwargs, id_ = _shared_memory(id_, size, create=create)
        mmap_ = mmap.mmap(*args, **kwargs)
        buf_ = memoryview(mmap_)
        fd_ = -1 if MS_WINDOWS else args[0]
        size_ = args[1]
        return [id_, fd_, mmap_, buf_, size_]

    def __lock__(self):
        self._header[3][:2] = SHORT_TRUE

    def __unlock__(self):
        self._header[3][:2] = SHORT_FALSE

    @property
    def __locked__(self):
        return bytes(self._header[3][:2]) == SHORT_TRUE

    @property
    def contents(self):
        self._update()
        return bytes(self._data[3][:])

    @contents.setter
    def contents(self, value):
        if not isinstance(value, bytes):
            if hasattr(value, '__bytes__'):
                value = value.__bytes__()
            else:
                try:
                    value = memoryview(value)
                except:
                    raise ValueError("'contents' can only be set to values that support the bytes or buffer protocols.") from None
        self._resize(len(value))
        self._data[3][:] = value

    def __getitem__(self, item):
        if item >= len(self._data[3]):
            return None
        return bytes(self._data[3][item])

    def __setitem__(self, key, value):
        if key >= len(self._data[3]):
            self._resize(key)
        self._data[3][key] = value

    def __delitem__(self, key):
        del self._data[3][key]

