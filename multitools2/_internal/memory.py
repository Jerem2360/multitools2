import ctypes
import sys
from typing import overload
from typing import Any as _IGNORE  # tell type checkers to ignore the type of what's annotated

from .errors import configure
from . import POS_ARG_ERR, TYPE_ERR
from .type_check import parse
from .interface import Buffer, SupportsIndex
from .. import *
from . import *


_PyBUF_READ = 0x100
_PyBUF_WRITE = 0x200


ctypes.pythonapi.PyMemoryView_FromMemory.argtypes = ctypes.c_void_p, ctypes.c_ssize_t, ctypes.c_int
ctypes.pythonapi.PyMemoryView_FromMemory.restype = ctypes.py_object


class SegvType:
    __read__ = None
    __write__ = None
    __none__ = None

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._name = 'none'
        return self

    def __init__(self, *args, **kwargs):
        raise TypeError("Type 'SegvType' cannot be instantiated.") from configure(depth=1)

    def __repr__(self):
        return f"<SegvType '{self._name}'>"

    def __bool__(self):
        return self._name != 'none'

    @classmethod
    def from_OSError(cls, exc) -> 'SegvType':
        if len(exc.args) and isinstance(exc.args[0], str):
            if exc.args[0].startswith('exception: access violation reading'):
                return cls.read  # type: ignore
            if exc.args[0].startswith('exception: access violation writing'):
                return cls.write  # type: ignore
        return cls.none  # type: ignore

    @property
    def verb(self):
        match self._name:
            case 'read':
                return 'reading'
            case 'write':
                return 'writing'
            case _:
                return 'none'

    @property
    def type(self):
        return self._name

    @classmethod
    @property
    def read(cls):
        if cls.__read__ is None:
            cls.__read__ = cls.__new__(cls)
            cls.__read__._name = 'read'
        return cls.__read__

    @classmethod
    @property
    def write(cls):
        if cls.__write__ is None:
            cls.__write__ = cls.__new__(cls)
            cls.__write__._name = 'write'
        return cls.__write__

    @classmethod
    @property
    def none(cls):
        if cls.__none__ is None:
            cls.__none__ = cls.__new__(cls)
        return cls.__none__


@scope_at(__NAME__)
class AccessViolationError(MemoryError):
    def __init__(self, address, segv_type):
        formatted = f"{segv_type.verb} at 0x{hex(address).removeprefix('0x').zfill(16).upper()}."
        super().__init__(formatted)
        self.address = address
        self.segv_type = segv_type
        self.formatted = formatted


def _validate_address(address) -> SegvType:
    if address < (256 ** 4):   # addresses of 4 bytes or fewer are usually not readable
        return SegvType.read  # type: ignore

    to_test = ctypes.cast(ctypes.c_void_p(address), ctypes.POINTER(ctypes.c_char))  # address to test is converted to char*
    temp = ctypes.create_string_buffer(0, 1)  # temporary copy buffer

    try:
        # we use memcpy to trigger an eventual access violation
        ctypes.cdll.msvcrt.memcpy(temp, to_test, 1)
    except OSError as e:
        msg = e.args
        if (len(msg) > 0) and isinstance(msg[0], str):
            if msg[0].startswith('exception: access violation reading'):
                # you can write only if you can read. Reverse is not true.
                return SegvType.read  # type: ignore
        raise

    try:
        # use memcpy the other way to trigger eventual writing access violation: we need to test for readonly memory
        ctypes.cdll.msvcrt.memcpy(to_test, temp, 1)
    except OSError as e:
        msg = e.args
        if (len(msg) > 0) and isinstance(msg[0], str):
            if msg[0].startswith('exception: access violation writing'):
                return SegvType.write  # type: ignore

        raise

    return SegvType.none  # type: ignore


def _validate_memory_block(address, size):
    for i in range(address, address + size):
        res = _validate_address(i)
        if res:
            return res
    return SegvType.none


def _my_hex(x):
    hex_ = hex(x).removeprefix('0x')
    if len(hex_) <= 1:
        hex_ = '0' + hex_
    return '0x' + hex_


def _buffer_get_pointer(buf):
    """
    Internal helper using the C api to fetch the pointer of a
    buffer object.
    """
    # parse_args((buf,), Buffer, depth=1)

    data = _Py_buffer()
    ctypes.pythonapi.PyObject_GetBuffer(ctypes.py_object(buf), ctypes.byref(data), ctypes.c_int(0))
    pointer = ctypes.c_ssize_t.from_address(ctypes.addressof(data)).value
    ctypes.pythonapi.PyBuffer_Release(ctypes.byref(data))
    return pointer


class _Py_buffer(ctypes.Structure):  # the Py_Buffer structure from the C api
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


class _BufferWrapper:
    """
    Wrapper around the Py_Buffer structure to make
    sure it is always released, no matter what.
    """
    def __init__(self, buffer, do_release=True):
        """
        Wrap the given Py_Buffer structure.
        """
        self._buf = buffer
        self._do_release = do_release
        self._released = False

    def __del__(self):
        """
        Destructor.
        Releases the buffer if it is not already done.
        """
        if not self._do_release:
            return
        self.release()

    def release(self):
        """
        Release the buffer.
        """
        if self._released:
            return
        try:
            ctypes.pythonapi.PyBuffer_Release(ctypes.byref(self._buf))
        except:
            pass
        self._released = True

    def is_alive(self):
        """
        Whether this buffer is not released yet
        and is still valid.
        """
        return not self._released

    @property
    def buf(self):
        return self._buf.buf

    @property
    def obj(self):
        return self._buf.obj

    @property
    def len(self):
        return self._buf.len

    @property
    def readonly(self):
        return self._buf.readonly

    @property
    def itemsize(self):
        return self._buf.itemsize

    @property
    def format(self):
        return self._buf.format

    @property
    def ndim(self):
        return self._buf.ndim


class Memory:
    """
    Provide a flat writable view on raw memory.
    While it supports write access of most objects'0
    raw data, it comes with some limitations:
    - it can only provide a view on python objects that support the buffer protocol (see the Buffer interface)
    - it cannot provide a view on read-only buffer objects
    - once the buffer is released, no operation can be done on the memory.

    In other words, Memory objects only write where and
    when the buffer's exporter allows to.
    However, you can do anything you want with a Memory
    object that owns its memory block.
    """
    @overload
    def __init__(self, size: int, auto_free: bool = True) -> None:
        """
        Allocate a new memory block of size bytes.
        """
    @overload
    def __init__(self, source: Buffer | object, auto_free: bool = True) -> None:
        """
        Wrap source with a Memory object.
        'source' must support the buffer protocol and be writable.
        """

    def __init__(self, *args, **kwargs):
        """
        Memory(integer_size) -> View on freshly allocated memory.
        Memory(buffer_object) -> View on the memory wrapped by buffer.

        Note: If provided, the source buffer object must be writable.
        """
        if len(args) != 1:
            raise TypeError(POS_ARG_ERR.format('Memory.__init__', 1, len(args))) from configure(1)

        self._do_free = kwargs.get('auto_free', True)
        if isinstance(args[0], Buffer):  # Memory(source: Buffer)
            source = args[0]

            if not isinstance(source, memoryview):
                source = memoryview(source)  # ensure our buffer is a memoryview object.

            # protect read-only buffers:
            if source.readonly:
                raise ValueError("Read-only memory.") from configure(1)

            # total number of bytes wrapped by the source buffer:
            size = source.itemsize * len(source)

            # We let the exporter know that we are using the contents of its buffer:
            buf = _Py_buffer()
            try:
                ctypes.pythonapi.PyObject_GetBuffer(ctypes.py_object(source), ctypes.byref(buf), ctypes.c_int(_PyBUF_WRITE))
            except:
                # if something failed, propagate the exception and release our Py_buffer object:
                old_err = sys.exc_info()[1]
                try:
                    ctypes.pythonapi.PyBuffer_Release(ctypes.byref(buf))
                except:
                    pass

                # raise err_depth(type(old_err), *old_err.args, depth=1) from None
                raise type(old_err)(*old_err.args) from configure(1)

            # wrap our Py_buffer object to ensure it gets released when self is freed:
            self._buf = _BufferWrapper(buf)

            # From now on, we own a Py_buffer object that will keep alive
            # its exporter (our source buffer object) as long as we don't
            # release it. Release is done in the destructor.

            # some arguments to pass in to PyMemoryView_FromMemory():
            ptr = self._buf.buf
            flags = _PyBUF_WRITE

            # we set the restype of the python api function so its return value is appropriately interpreted:
            ctypes.pythonapi.PyMemoryView_FromMemory.restype = ctypes.py_object
            try:
                mv = ctypes.pythonapi.PyMemoryView_FromMemory(ctypes.c_void_p(ptr), ctypes.c_ssize_t(size), ctypes.c_int(flags))
            except:
                # if something went wrong, release our buffer and propagate the exception:
                old_err = sys.exc_info()[1]
                self._buf.release()
                raise type(old_err)(*old_err.args) from configure(1)

            # self._view is guaranteed to be writable (see flags) and 1-dimensional.
            # self._view.itemsize is also guaranteed to be 1:
            self._view = mv
            return
        if isinstance(args[0], SupportsIndex):  # Memory(size: SupportsIndex)
            size = args[0].__index__()
            self._view = memoryview(bytearray(size))
            self._buf = None  # no need to free ourselves, it is done by the bytearray() instance.
            return

        raise TypeError(TYPE_ERR.format('Buffer | SupportsIndex', type(args[0]).__name__)) from configure(1)

    def __del__(self):
        """
        Implement del self
        """
        if not self._do_free:
            return
        try:
            self.release()
        except:
            pass

    @overload
    def __getitem__(self, item: int | SupportsIndex) -> int: ...
    @overload
    def __getitem__(self, item: slice) -> list[int]: ...

    def __getitem__(self, item) -> _IGNORE:
        """
        Implement self[item]
        """
        parse(SupportsIndex | slice, item)

        self._ensure_alive(1)
        if isinstance(item, slice):
            start = item.start if item.start is not None else 0
            stop = item.stop if item.stop is not None else len(self._view)
            step = item.step if item.step is not None else 1

            mv = self._view[start:stop:step]
            return list(i for i in mv)

        return self._view[item.__index__()]

    @overload
    def __setitem__(self, key: int | SupportsIndex, value: int | bytes | SupportsIndex) -> None: ...
    @overload
    def __setitem__(self, key: slice, value: bytes | list[int | SupportsIndex]) -> None: ...

    def __setitem__(self, key, value):
        """
        Implement self[key] = value
        """
        parse(slice | SupportsIndex, list[SupportsIndex] | bytes | SupportsIndex, key, value)
        self._ensure_alive(1)
        if isinstance(key, slice):
            start = key.start if key.start is not None else 0
            stop = key.stop if key.stop is not None else len(self._view)
            step = key.step if key.step is not None else 1

            mv = self._view[start:stop:step]

            if len(value) != len(mv):
                raise ValueError("value must have the same length as the memory slice.") from configure(1)

            if not isinstance(value, bytes):
                value_b = b''
                for i in value:
                    i = i.__index__()
                    if i >= 256:
                        raise OverflowError(f"Integer {i} too big to fit in one byte.") from configure(1)
                    value_b += i.to_bytes(1, sys.byteorder)
            else:
                value_b = value
            mv[:] = value_b
            return

        self._view[key.__index__()] = value.__index__()

    def __delitem__(self, key: int | SupportsIndex | slice):
        """
        Implement del self[item]
        """
        parse(SupportsIndex | slice, key)

        self._ensure_alive(1)
        if isinstance(key, slice):
            start = key.start if key.start is not None else 0
            stop = key.stop if key.stop is not None else len(self._view)
            step = key.step if key.step is not None else 1

            self._view[start:stop:step] = b'\x00' * len(self._view[start:stop:step])
            return

        self._view[key.__index__()] = 0

    def __bytes__(self):
        """
        Implement bytes(self)
        """
        self._ensure_alive(1)
        return bytes(self._view)

    def __len__(self):
        """
        Implement len(self)
        """
        self._ensure_alive(1)
        return len(self._view)

    def __repr__(self):
        """
        Implement repr(self)
        """
        try:
            self._ensure_alive()
        except:
            return f"<released 'Memory' object at {hex(id(self))}>"
        addr = self._buf.buf if self._buf is not None else _buffer_get_pointer(self._view)
        if len(self) > 10:
            return f"<memory at {hex(addr)}: [{' '.join(_my_hex(i) for i in self._view[:10])} ...]>".replace('[', '{').replace(']', '}')
        return f"<memory at {hex(addr)}: [{' '.join(_my_hex(i) for i in self._view)}]>".replace('[', '{').replace(']', '}')

    def _ensure_alive(self, depth=0):
        try:
            len(self._view)
        except ValueError:
            raise PermissionError("Access denied: memory is released.") from configure(depth + 1)

    def view(self):
        """
        Return a memoryview object pointing to the memory.
        The memoryview object will present the memory as
        raw bytes (itemsize=1,ndim=1,len=len(self)).
        """
        self._ensure_alive(1)
        return self._view

    def get_segment(self, segment: slice | range):
        """
        Return the given segment of the memory.
        """
        parse(slice | range, segment)
        try:
            mem = self._view[segment.start:segment.stop:segment.step]
        except Exception as e:
            raise e from configure(depth=1)
        return Memory(mem, auto_free=False)

    def copy(self):
        """
        Copy the bytes stored here into a newly allocated memory block.
        """
        res = Memory(len(self))
        res[:] = self[:]
        return res

    @classmethod
    def at_address(cls, address: int | SupportsIndex, size: int | SupportsIndex, auto_free=True):
        """
        Wrap the memory block at given address with given size.
        Access violations are handled and are replaced with AccessViolationError

        **Caution: Using this function inappropriately can break the interpreter.
        Only use when you know exactly what you're doing.**
        """
        parse(SupportsIndex, SupportsIndex, bool, address, size, auto_free)
        segv_type = _validate_memory_block(address.__index__(), size.__index__())
        if segv_type:
            raise AccessViolationError(address, segv_type) from configure(depth=1)

        result = cls.__new__(cls)
        result._do_free = auto_free

        try:
            result._view = ctypes.pythonapi.PyMemoryView_FromMemory(
                ctypes.c_void_p(address.__index__()),
                ctypes.c_ssize_t(size.__index__()),
                ctypes.c_int(_PyBUF_WRITE)
            )
        except OSError as e:
            segv_type = SegvType.from_OSError(e)
            if segv_type:
                raise AccessViolationError(address.__index__(), segv_type) from configure(depth=1)

        result._buf = None
        return result


    def release(self):
        """
        Release the memory and buffers associated with it.
        """
        self._view.release()
        if self._buf is None:
            return
        self._buf.release()

    @property
    def address(self):
        """
        The address of the memory block.
        This is zero for released memory.
        """
        try:
            self._ensure_alive()
        except:
            return 0
        if self._buf is None:
            return _buffer_get_pointer(self._view.obj)  # we own ourselves, so our buffer object is necessarily a bytearray
        return self._buf.buf

    @property
    def obj(self) -> Buffer | None:
        """
        The object from which the memory was borrowed if it
        is not owned, else None.
        """
        if self._buf is None:
            return None

        if self._buf.obj == 0:  # we check for a NULL pointer, which would mean no source object.
            return None

        try:
            obj_ = ctypes.cast(self._buf.obj, ctypes.py_object)
            return obj_.value
        except:
            return None

