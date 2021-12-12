from typing import Generic as _Generic, TypeVar as _TypeVar, Any as _Any
from ..functional import abstractmethod as _abstractmethod
from ctypes import c_void_p as _void_p, \
    c_char as _char


_T = _TypeVar("_T")


class _CData(_Generic[_T]):
    def __ctypes_from_outparam__(self) -> _T: ...

    def __hash__(self): ...

    def __reduce__(self): ...

    def __setstate__(self, state): ...

    @property
    def _b_base_(self) -> _Any: ...

    @property
    def _b_needsfree_(self) -> int: ...

    @property
    def _objects(self) -> _Any: ...


class CObject(object):

    __slots__ = ["__data"]
    __orig_type__: type[_CData] = ...

    def __init__(self, data: bytes):...

    def __init_subclass__(cls, **kwargs): ...

    @_abstractmethod
    def __c__(self, *args, **kwargs) -> _CData: ...

    def _get(self) -> bytes: ...


class CVoidPtr(CObject):
    __orig_type__ = ...

    __slots__ = ["_ptr"]
    def __init__(self, address: int): ...

    def __c__(self, *args, **kwargs) -> _void_p: ...

    @staticmethod
    def from_object(obj: _Any) -> CVoidPtr: ...

    @property
    def address(self) -> int: ...


class PyObject(CObject):
    __orig_type__ = ...

    __slots__ = ["_ptr"]
    def __init__(self, obj: _Any): ...

    def __c__(self, *args, **kwargs) -> _void_p: ...

    @property
    def address(self) -> int: ...


class CChar(CObject):
    __orig_type__ = ...

    def __init__(self, value: str): ...

    def __c__(self) -> _char: ...

    @property
    def value(self) -> str: ...

