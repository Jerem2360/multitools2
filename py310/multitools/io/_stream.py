from .._meta import MultiMeta, AbstractMethodDescriptor as abstractmethod
from . import _buffer
from .._type_check import typecheck


class Stream(metaclass=MultiMeta):
    @abstractmethod
    def __gethandle__(self):
        pass

    @property
    def handle(self):
        return self.__gethandle__()

    @property
    def readable(self):
        return hasattr(self, "__read__")

    @property
    def writable(self):
        return hasattr(self, "__write__")


class OStream(Stream, metaclass=MultiMeta):

    @abstractmethod
    def __write__(self, data, **kwargs):
        pass

    def write(self, data, **kwargs):
        return self.__write__(data, **kwargs)


class IStream(Stream, metaclass=MultiMeta):

    @abstractmethod
    def __read__(self, size, **kwargs):
        pass

    def read(self, size, **kwargs):
        typecheck(size, (int,), target_name="size")
        return self.__read__(size, **kwargs)

    def readline(self, **kwargs):
        pass


class TextOutput(OStream, metaclass=MultiMeta):
    def __init__(self, buffer):
        typecheck(buffer, (_buffer.StrBuffer, _buffer.Buffer), target_name="buffer")
        self._handle = buffer

    def __gethandle__(self):
        return self._handle

    def __write__(self, data, encoding=None):
        typecheck(data, (str,), target_name="data")
        typecheck(encoding, (str, type(None)), target_name="encoding")
        return self._handle.write(data, encoding=encoding)


class TextInput(IStream, metaclass=MultiMeta):
    def __init__(self, buffer):
        typecheck(buffer, (_buffer.StrBuffer, _buffer.Buffer), target_name="buffer")
        self._handle = buffer

    def __gethandle__(self):
        return self._handle

    def __read__(self, size, encoding=None):
        typecheck(encoding, (str, type(None)), target_name="encoding")
        typecheck(size, (int,), target_name="size")
        return self._handle.read(size, encoding=encoding)


class TextIO(TextOutput, TextInput, metaclass=MultiMeta):
    pass


class BytesOutput(OStream, metaclass=MultiMeta):
    def __init__(self, buffer):
        typecheck(buffer, (_buffer.BytesBuffer,), target_name="buffer")
        self._handle = buffer

    def __gethandle__(self):
        return self._handle

    def __write__(self, data, **kwargs):
        typecheck(data, (bytes,), target_name="data")
        return self._handle.write(data, **kwargs)


class BytesInput(IStream, metaclass=MultiMeta):
    def __init__(self, buffer):
        typecheck(buffer, (_buffer.BytesBuffer,), target_name="buffer")
        self._handle = buffer

    def __gethandle__(self):
        return self._handle

    def __read__(self, size, **kwargs):
        typecheck(size, (int,), target_name="size")
        return self._handle.read(size, **kwargs)


class BytesIO(BytesOutput, BytesInput, metaclass=MultiMeta):
    pass


class FileOutput(OStream, metaclass=MultiMeta):
    def __init__(self, buffer):
        typecheck(buffer, (_buffer.FileBuffer,), target_name="buffer")
        self._handle = buffer

    def __gethandle__(self):
        return self._handle

    def __write__(self, data, encoding=None):
        typecheck(encoding, (str, type(None)), target_name="encoding")
        typecheck(data, (str,), target_name="data")
        return self._handle.write(data, encoding=encoding)

    fileno = property(lambda self: self._handle.fd)
    closed = property(lambda self: self._handle.closed)


class FileInput(IStream, metaclass=MultiMeta):
    def __init__(self, buffer):
        typecheck(buffer, (_buffer.FileBuffer,), target_name="buffer")
        self._handle = buffer

    def __gethandle__(self):
        return self._handle

    def __read__(self, size, encoding=None):
        typecheck(encoding, (str, type(None)), target_name="encoding")
        typecheck(size, (int,), target_name="size")
        return self._handle.read(size, encoding=encoding)

    def readline(self, encoding=None):
        typecheck(encoding, (str, type(None)), target_name="encoding")
        return self._handle.readline(encoding=encoding)

    fileno = property(lambda self: self._handle.fd)
    closed = property(lambda self: self._handle.closed)


class FileIO(FileOutput, FileInput, metaclass=MultiMeta):
    pass

