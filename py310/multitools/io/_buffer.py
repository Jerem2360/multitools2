import sys

from .._meta import MultiMeta, AbstractMethodDescriptor as abstractmethod
from .._type_check import typecheck

import sys as _sys
from os import open as _open, read as _read, write as _write, close as _close


class Buffer(metaclass=MultiMeta):
    @abstractmethod
    def read(self, size, **kwargs):
        pass

    @abstractmethod
    def write(self, data, **kwargs):
        pass

    def readline(self, **kwargs):
        result = b""
        newline = b"\n"
        while True:
            dat = self.read(1, **kwargs)
            encoding = kwargs.get("encoding", sys.getdefaultencoding())
            if encoding is None:
                encoding = sys.getdefaultencoding()
            if isinstance(dat, str) and (not isinstance(result, str)):
                result = str(result, encoding=encoding)
            result += dat
            if isinstance(result, str):
                newline = "\n"
            if dat.endswith(newline):
                break

        return result.removesuffix(newline)


class BytesBuffer(Buffer, metaclass=MultiMeta):
    def __init__(self, value=b""):
        typecheck(value, (bytes,), target_name="value")
        self._contents = value

    def read(self, size, **kwargs):
        typecheck(size, (int,), target_name="size")
        result = b""
        for i in range(size):
            num = len(self._contents) - i
            if num < 0:
                raise BufferError("Not enough bytes to read.")
            result += self._contents[num]

        self._contents.removesuffix(result)
        return result

    def write(self, data, **kwargs):
        typecheck(data, (bytes,), target_name="data")
        self._contents += data
        return len(data)


class StrBuffer(BytesBuffer, metaclass=MultiMeta):
    def __init__(self, value="", encoding=_sys.getdefaultencoding()):
        typecheck(value, (str,), target_name="value")
        typecheck(encoding, (str,), target_name="encoding")
        self._encoding = encoding
        super().__init__(value=bytes(value, encoding=encoding))

    def read(self, size, encoding=None):
        typecheck(size, (int,), target_name="size")
        typecheck(encoding, (str, type(None)), target_name="encoding")
        res = super().read(size)
        if encoding is None:
            encoding = self._encoding
        return str(res, encoding=encoding)

    def write(self, data, encoding=None):
        typecheck(data, (str,), target_name="data")
        typecheck(encoding, (str, type(None)), target_name="encoding")
        if encoding is None:
            encoding = self._encoding
        return super().write(bytes(data, encoding=encoding))

    encoding = property(lambda self: self._encoding)


class FileBuffer(Buffer, metaclass=MultiMeta):
    def __init__(self, arg1, closefd=None, encoding=_sys.getdefaultencoding()):
        typecheck(closefd, (bool, type(None)), target_name="closefd")
        typecheck(encoding, (str,), target_name="encoding")
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
        raise TypeError(f"Expected type Union[int, str], got {type(arg1)} instead.")

    def read(self, size, encoding=None):
        typecheck(size, (int,), target_name="size")
        typecheck(encoding, (str, type(None)), target_name="encoding")
        if self._open:
            res = _read(self._fileno, size)
            if encoding is None:
                encoding = self._encoding

            return str(res, encoding=encoding)
        raise SystemError("IO operation on closed file.")

    def write(self, data, encoding=None):
        typecheck(data, (str,), target_name="data")
        typecheck(encoding, (str, type(None)), target_name="encoding")
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

