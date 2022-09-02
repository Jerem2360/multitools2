from multitools.interop._mem import Memory
import multitools
import ctypes


# multitools._debug("TYPE_CHECK/debug")


mem = Memory(4)

print(mem)

x = ctypes.c_int.from_buffer(mem.view())

print(x)

mem[1] = 1

print(x, mem)


"""import ctypes
import struct


class _Py_buffer(ctypes.Structure):
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


def _buffer_get_pointer(buf):
    ""
    Internal helper using the C api to fetch the pointer of a
    buffer object.
    ""
    # parse_args((buf,), Buffer, depth=1)

    data = _Py_buffer()
    ctypes.pythonapi.PyObject_GetBuffer(ctypes.py_object(buf), ctypes.byref(data), ctypes.c_int(0))
    pointer = ctypes.c_ssize_t.from_address(ctypes.addressof(data)).value
    ctypes.pythonapi.PyBuffer_Release(ctypes.byref(data))
    return pointer


x = ctypes.c_long(10)
source = memoryview(x)

print(bytes(source))

size = len(source) * source.itemsize
flags = 0x200  # _PyBUF_WRITE

buf = _Py_buffer()

ctypes.pythonapi.PyObject_GetBuffer(ctypes.py_object(source), ctypes.byref(buf))

ptr = buf.buf

ctypes.pythonapi.PyMemoryView_FromMemory.restype = ctypes.py_object

mv = ctypes.pythonapi.PyMemoryView_FromMemory(ctypes.c_void_p(ptr), ctypes.c_ssize_t(size), ctypes.c_int(flags))

print(bytes(mv))


x.value = 18

print(bytes(source), bytes(mv))
print(mv.itemsize, len(mv), mv.readonly)
print(source.itemsize, len(source), source.readonly)

ctypes.pythonapi.PyBuffer_Release(ctypes.byref(buf))
"""
