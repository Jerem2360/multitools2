from .._multi_class import MultiMeta as _MultiMeta, AbstractMethodDescriptor as _abstractmethod
from . import _buffer
from .._type_check import typecheck as _typecheck


class Stream(metaclass=_MultiMeta):
    @_abstractmethod
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


class OStream(Stream, metaclass=_MultiMeta):

    @_abstractmethod
    def __write__(self, data, **kwargs):
        pass

    def write(self, data, **kwargs):
        return self.__write__(data, **kwargs)


class IStream(Stream, metaclass=_MultiMeta):

    @_abstractmethod
    def __read__(self, size, **kwargs):
        pass

    def read(self, size, **kwargs):
        return self.__read__(size, **kwargs)

    def readline(self, **kwargs):
        pass


class TextOutput(OStream, metaclass=_MultiMeta):
    def __init__(self, buffer):
        _typecheck(buffer, (_buffer.StrBuffer, _buffer.Buffer), target_name="buffer")
        self._handle = buffer

    def __gethandle__(self):
        return self._handle

    def __write__(self, data, encoding=None):
        _typecheck(data, (str,), target_name="data")
        _typecheck(encoding, (str, type(None)), target_name="encoding")
        return self._handle.write(data, encoding=encoding)


class TextInput(IStream, metaclass=_MultiMeta):
    def __init__(self, buffer):
        _typecheck(buffer, (_buffer.StrBuffer, _buffer.Buffer), target_name="buffer")
        self._handle = buffer

    def __gethandle__(self):
        return self._handle

    def __read__(self, size, encoding=None):
        _typecheck(encoding, (str, type(None)), target_name="encoding")
        _typecheck(size, (int,), target_name="size")
        return self._handle.read(size, encoding=encoding)


class TextIO(TextOutput, TextInput, metaclass=_MultiMeta):
    pass


class BytesOutput(OStream, metaclass=_MultiMeta):
    def __init__(self, buffer):
        _typecheck(buffer, (_buffer.BytesBuffer,), target_name="buffer")
        self._handle = buffer

    def __gethandle__(self):
        return self._handle

    def __write__(self, data, **kwargs):
        _typecheck(data, (bytes,), target_name="data")
        return self._handle.write(data, **kwargs)


class BytesInput(IStream, metaclass=_MultiMeta):
    def __init__(self, buffer):
        _typecheck(buffer, (_buffer.BytesBuffer,), target_name="buffer")
        self._handle = buffer

    def __gethandle__(self):
        return self._handle

    def __read__(self, size, **kwargs):
        _typecheck(size, (int,), target_name="size")
        return self._handle.read(size, **kwargs)


class BytesIO(BytesOutput, BytesInput, metaclass=_MultiMeta):
    pass


class FileOutput(OStream, metaclass=_MultiMeta):
    def __init__(self, buffer):
        _typecheck(buffer, (_buffer.FileBuffer,), target_name="buffer")
        self._handle = buffer

    def __gethandle__(self):
        return self._handle

    def __write__(self, data, encoding=None):
        _typecheck(encoding, (str, type(None)), target_name="encoding")
        _typecheck(data, (str,), target_name="data")
        return self._handle.write(data, encoding=encoding)

    fileno = property(lambda self: self._handle.fd)
    closed = property(lambda self: self._handle.closed)


class FileInput(IStream, metaclass=_MultiMeta):
    def __init__(self, buffer):
        _typecheck(buffer, (_buffer.FileBuffer,), target_name="buffer")
        self._handle = buffer

    def __read__(self, size, encoding=None):
        _typecheck(encoding, (str, type(None)), target_name="encoding")
        _typecheck(size, (int,), target_name="size")
        return self._handle.read(size, encoding=encoding)

    def readline(self, encoding=None):
        _typecheck(encoding, (str, type(None)), target_name="encoding")
        return self._handle.readline(encoding=encoding)

    fileno = property(lambda self: self._handle.fd)
    closed = property(lambda self: self._handle.closed)


class FileIO(FileOutput, FileInput, metaclass=_MultiMeta):
    pass

