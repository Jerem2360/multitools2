import ctypes
import mmap
import random

from ..interop import _mem
from .. import *
from ..errors._errors import err_depth
from . import _c_mem


__all__ = [
    "Memory",
    "SharedMemory"
]


class _MemId:
    def __init__(self, value: bytes):
        self._val = value

    def __int__(self):
        return int.from_bytes(self._val, _DEFAULT_BYTEORDER, signed=False)

    def __str__(self):
        return str(self._val, encoding='ascii').replace('\x00', '0')


def random_bytes(size):
    res = b""
    for i in range(size):
        res += random.randint(0, 127).to_bytes(1, _DEFAULT_BYTEORDER, signed=False)
    return res


Memory = _mem.Memory


class SharedNamespace:
    def __init__(self, memory):
        self._mem = memory


class SharedMemory:
    def __init__(self, size):
        _map = mmap.mmap(-1, size, access=mmap.ACCESS_WRITE)
        self._mem = Memory(_map)
        self._closer = _map.close

    def __bytes__(self):
        return bytes(self._mem)

    def __hash__(self):
        return self.address + 0xFF

    def __getitem__(self, item):
        return self._mem[item]

    def __setitem__(self, key, value):
        self._mem[key] = value

    def __delitem__(self, key):
        del self._mem[key]

    @classmethod
    def open(cls, memory_id):
        full_data = memory_id.to_bytes(17, _DEFAULT_BYTEORDER, signed=True)
        sz_data, addr_data = full_data[:8], full_data[8:16]
        size = int.from_bytes(sz_data, _DEFAULT_BYTEORDER, signed=False)
        address = int.from_bytes(addr_data, _DEFAULT_BYTEORDER, signed=False)
        if full_data[-1] != 255:
            raise err_depth(ValueError, "Invalid memory id.", depth=1)

        try:
            ctypes.pythonapi.PyMemoryView_FromMemory.restype = ctypes.py_object
            view = ctypes.pythonapi.PyMemoryView_FromMemory(ctypes.c_void_p(address), ctypes.c_ssize_t(size), ctypes.c_int(0x200))
            # this is guaranteed to be a memoryview
        except Exception as e:
            raise err_depth(type(e), *e.args, depth=1)

        self = cls.__new__(cls)
        self._mem = Memory(view)
        return self

    def release(self):
        self._mem.release()

    @property
    def address(self):
        return self._mem.address

    @property
    def id(self):
        addr_data = self.address.to_bytes(8, _DEFAULT_BYTEORDER, signed=False)
        sz_data = len(self._mem).to_bytes(8, _DEFAULT_BYTEORDER, signed=False)
        full_data = sz_data + addr_data + b'\xFF'
        return int.from_bytes(full_data, _DEFAULT_BYTEORDER, signed=True)

