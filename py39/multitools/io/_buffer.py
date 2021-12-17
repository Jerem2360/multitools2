from .._multi_class import MultiMeta as _MultiMeta, AbstractMethodDescriptor as _abstractmethod

import sys as _sys
from os import open as _open, read as _read, write as _write, close as _close


class Buffer(metaclass=_MultiMeta):
    @_abstractmethod
    def read(self, size, **kwargs):
        pass

    @_abstractmethod
    def write(self, data, **kwargs):
        pass

    def readline(self, **kwargs):
        result = b""
        while True:
            dat = self.read(1, **kwargs)
            result += dat
            if dat.endswith(b"\n"):
                break

        return result.removesuffix(b"\n")


class BytesBuffer(Buffer, metaclass=_MultiMeta):
    def __init__(self, value=b""):
        self._contents = value

    def read(self, size, **kwargs):
        result = b""
        for i in range(size):
            num = len(self._contents) - i
            if num < 0:
                raise BufferError("Not enough bytes to read.")
            result += self._contents[num]

        self._contents.removesuffix(result)
        return result

    def write(self, data, **kwargs):
        self._contents += data
        return len(data)


class StrBuffer(BytesBuffer):
    def __init__(self, value: str = "", encoding=_sys.getdefaultencoding()):
        self._encoding = encoding
        super().__init__(value=bytes(value, encoding=encoding))

    def read(self, size, encoding=None):
        res = super().read(size)
        if encoding is None:
            encoding = self._encoding
        return str(res, encoding=encoding)

    def write(self, data, encoding=None):
        if encoding is None:
            encoding = self._encoding
        return super().write(bytes(data, encoding=encoding))

    encoding = property(lambda self: self._encoding)


class FileBuffer(Buffer, metaclass=_MultiMeta):
    def __init__(self, arg1, closefd=None, encoding=_sys.getdefaultencoding()):
        self._closefd = closefd
        self._open = True
        self._encoding = encoding
        if isinstance(arg1, int):
            self._fileno = arg1

            if self._closefd is None:
                self._closefd = False  # borrowed file descriptor (we've been given one)
            return

        if isinstance(arg1, str):
            self._fileno = _open(arg1, 0)

            if self._closefd is None:
                self._closefd = True  # owned file descriptor (we've opened our own file)
            return

    def read(self, size, encoding=None):
        if self._open:
            res = _read(self._fileno, size)
            if encoding is None:
                encoding = self._encoding

            return str(res, encoding=encoding)
        raise SystemError("IO operation on closed file.")

    def write(self, data, encoding=None):
        if self._open:
            if encoding is None:
                encoding = self._encoding
            return _write(self._fileno, bytes(data, encoding=encoding))
        raise SystemError("IO operation on closed file.")

    def close(self):
        if self._closefd and self._open:
            _close(self._fileno)
            self._open = False

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    closed = property(lambda self: not self._open)
    fd = property(lambda self: self._fileno)
    encoding = property(lambda self: self._encoding)

