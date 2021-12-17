from .._multi_class import MultiMeta as _MultiMeta, AbstractMethodDescriptor as _abstractmethod
from typing import Generic as _Generic, TypeVar as _TypeVar, Optional as _Optional
from . import _buffer


_T = _TypeVar("_T")


class Stream(_Generic[_T], metaclass=_MultiMeta):
    @_abstractmethod
    def __gethandle__(self) -> _buffer.Buffer[_T]: ...
    @property
    def handle(self) -> _buffer.Buffer[_T]: ...
    @property
    def readable(self) -> bool: ...
    @property
    def writable(self) -> bool: ...


class OStream(Stream, metaclass=_MultiMeta):
    @_abstractmethod
    def __write__(self, data: _T, **kwargs) -> int: ...
    def write(self, data: _T, **kwargs) -> int: ...


class IStream(Stream, metaclass=_MultiMeta):
    @_abstractmethod
    def __read__(self, size: int, **kwargs) -> _T: ...
    def read(self, size: int, **kwargs) -> _T: ...
    def readline(self, **kwargs) -> _Optional[_T]: ...


class TextOutput(OStream[str], metaclass=_MultiMeta):
    def __init__(self, buffer: _buffer.Buffer[str]) -> None: ...
    def __gethandle__(self) -> _buffer.Buffer[str]: ...
    def __write__(self, data: str, **kwargs) -> int: ...


class TextInput(IStream[str], metaclass=_MultiMeta):
    def __init__(self, buffer: _buffer.Buffer[str]) -> None: ...
    def __gethandle__(self) -> _buffer.Buffer[str]: ...
    def __read__(self, size: int, **kwargs) -> str: ...


class TextIO(TextOutput, TextInput, metaclass=_MultiMeta): ...


class BytesOutput(OStream[bytes], metaclass=_MultiMeta):
    def __init__(self, buffer: _buffer.Buffer[bytes]) -> None: ...
    def __gethandle__(self) -> _buffer.Buffer[bytes]: ...
    def __write__(self, data: bytes, **kwargs) -> int: ...


class BytesInput(IStream[bytes], metaclass=_MultiMeta):
    def __init__(self, buffer: _buffer.Buffer[bytes]) -> None: ...
    def __gethandle__(self) -> _buffer.Buffer[bytes]: ...
    def __read__(self, size: int, **kwargs) -> bytes: ...


class BytesIO(BytesOutput, BytesInput, metaclass=_MultiMeta): ...


class FileOutput(OStream[str], metaclass=_MultiMeta):
    def __init__(self, buffer: _buffer.FileBuffer) -> None: ...
    def __gethandle__(self) -> _buffer.FileBuffer: ...
    def __write__(self, data: str, encoding: _Optional[str] = ...) -> int: ...
    @property
    def fileno(self) -> int: ...
    @property
    def closed(self) -> bool: ...


class FileInput(IStream[str], metaclass=_MultiMeta):
    def __init__(self, buffer: _buffer.FileBuffer) -> None: ...
    def __gethandle__(self) -> _buffer.FileBuffer: ...
    def __read__(self, size: int, encoding: _Optional[str] = ...) -> str: ...
    def readline(self, encoding: _Optional[str] = ...) -> str:


class FileIO(FileOutput, FileInput, metaclass=_MultiMeta): ...
