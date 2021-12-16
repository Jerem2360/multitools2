from .._multi_class import MultiMeta as _MultiMeta, AbstractMethodDescriptor as _abstractmethod
from typing import TypeVar as _TypeVar, Generic as _Generic, overload as _overload, Optional as _Optional
from types import TracebackType as _TracebackType


_T = _TypeVar("_T")


class Buffer(_Generic[_T], metaclass=_MultiMeta):
    @_abstractmethod
    def read(self, size: int, **kwargs) -> _T: ...
    @_abstractmethod
    def write(self, data: _T, **kwargs) -> int: ...
    def readline(self, **kwargs) -> _T: ...


class BytesBuffer(Buffer[bytes], metaclass=_MultiMeta):
    def __init__(self, value: bytes = ...) -> None: ...
    def read(self, size: int, **kwargs) -> bytes: ...
    def write(self, data: bytes, **kwargs) -> int: ...


class StrBuffer(Buffer[str], metaclass=_MultiMeta):
    def __init__(self, value: str = ...) -> None: ...
    def read(self, size: int, encoding: _Optional[str] = ...) -> str: ...
    def write(self, data: str, encoding: _Optional[str] = ...) -> int: ...
    @property
    def encoding(self) -> str: ...


class FileBuffer(Buffer[str], metaclass=_MultiMeta):
    @_overload
    def __init__(self, fdescr: int, closefd: bool = ..., encoding: str = ...) -> None: ...
    @_overload
    def __init__(self, fpath: str, closefd: bool = ..., encoding: str = ...) -> None: ...
    def read(self, size: int, encoding: _Optional[str] = ...) -> str: ...
    def write(self, data: str, encoding: _Optional[str] = ...) -> int: ...
    def close(self) -> None: ...
    def __del__(self) -> None: ...
    def __enter__(self) -> None: ...
    def __exit__(self, exc_type: type[Exception], exc_val: Exception, exc_tb: _TracebackType) -> None: ...
    @property
    def closed(self) -> bool: ...
    @property
    def fd(self) -> int: ...
    @property
    def encoding(self) -> str: ...
