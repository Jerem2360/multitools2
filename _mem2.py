import ctypes
import sys
import weakref

import _ctypes

ctypes.pythonapi.PyMemoryView_FromMemory.argtypes = (ctypes.c_void_p, ctypes.c_ssize_t, ctypes.c_int)
ctypes.pythonapi.PyMemoryView_FromMemory.restype = ctypes.py_object

_PyBUF_READ = 0x100
_PyBUF_WRITE = 0x200


class _MyWeakRef:
    def __init__(self, obj):
        self._id = id(obj)
        self._tp = weakref.ref(type(obj))

    def __call__(self, *args, **kwargs):
        if not self._id:
            return
        if not self._tp():
            return
        tp = self._tp()
        obj = _ctypes.PyObj_FromPtr(self._id)
        if obj.__class__ != tp:
            return

        return obj


class _Py_buffer(ctypes.Structure):  # the Py_Buffer structure from the C api
    _fields_ = (
        ("buf", ctypes.c_void_p),
        ("obj", ctypes.py_object),
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
    def __init__(self, buf):
        self._freed = False
        self._initialized = False
        buffer = _BufferWrapper(_Py_buffer())
        try:
            ctypes.pythonapi.PyObject_GetBuffer(ctypes.py_object(buf), ctypes.byref(buffer._buf), ctypes.c_int(_PyBUF_WRITE))
        except:
            raise TypeError("First parameter must be a buffer object.")

        if memoryview(buf).readonly:
            ctypes.pythonapi.PyBuffer_Release(ctypes.byref(buffer._buf))
            raise TypeError("Buffer must be writable.")

        mv = ctypes.pythonapi.PyMemoryView_FromMemory(buffer.buf, buffer.len, _PyBUF_WRITE)
        self._view = mv
        if type(buf).__weakrefoffset__:
            self._obj = weakref.ref(buf)
        else:
            self._obj = _MyWeakRef(buf)
        self._owned = False
        self._initialized = True

    @classmethod
    def allocate(cls, size):
        obj = bytearray(size)
        res = cls(obj)
        _ctypes.Py_INCREF(obj)
        res._owned = True
        return res

    def free(self):
        self._view.release()
        if self._owned and (self.obj is not None):
            _ctypes.Py_DECREF(self.obj)
        self._freed = True

    @property
    def obj(self) -> object | None:
        return self._obj()

    def __repr__(self):
        res = '{ '
        nloop = 0
        for i in self._view:
            nloop += 1
            if nloop <= 8:
                res += hex(i) + ' '

        if nloop > 8:
            res += '... '
        res += '}'
        return res

    def __del__(self):
        if not self._freed:
            self.free()

