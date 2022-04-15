from typing import Protocol as _Proto, Any as _Any
from ctypes import Array


# virtual type:
class _PyCArg(object):
    # noinspection PyMethodParameters
    @staticmethod
    def __new__(*args, **kwargs) -> _PyCArg: ...
    def __repr__(self) -> str: ...
    _obj: object = ...


class _Dll(_Proto):
    _handle: int = ...


class CData(object):
    def __new__(cls, *args, **kwargs) -> CData: ...
    def __ctypes_from_outparam__(self, *args) -> CData: ...
    def __reduce__(self, *args) -> tuple: ...
    def __setstate__(self, np: dict, data: str) -> None: ...
    _b_base_: object = ...
    _b_needsfree_: int = ...
    _objects: object = ...


class PyCSimpleType(type):
    def __new__(mcs, *args, **kwargs) -> PyCSimpleType: ...
    def __mul__(cls, other: int) -> Array: ...  ## return is PyCArrayType
    def __imul__(cls, other: int) -> Array: ...
    def from_address(cls, value: int) -> SimpleCData: ...
    def from_buffer(cls, obj: _Any, offset: int = 0) -> SimpleCData: ...
    def from_buffer_copy(cls, obj: _Any, offset: int = 0) -> SimpleCData: ...
    def from_param(cls, value: _PyCArg | _Any) -> SimpleCData: ...
    def in_dll(cls, dll: _Dll, name: str) -> SimpleCData: ...


class SimpleCData(CData, metaclass=PyCSimpleType):
    def __new__(cls, *args, **kwargs) -> SimpleCData: ...
    def __bool__(self) -> bool: ...
    def __ctypes_from_outparam__(self, *args) -> SimpleCData: ...
    def __repr__(self) -> str: ...
    value: _Any = ...
    _as_parameter_: tuple | CData = ...


class PyCArrayType(type):
    def __new__(mcs, *args, **kwargs) -> PyCArrayType: ...
    def __mul__(cls, other: int) -> Array: ...  ## return is PyCArrayType
    def __imul__(cls, other: int) -> Array: ...
    def from_address(cls, value: int) -> Array: ...
    def from_buffer(cls, obj: _Any, offset: int = 0) -> Array: ...
    def from_buffer_copy(cls, obj: _Any, offset: int = 0) -> Array: ...
    def from_param(cls, value: _PyCArg | _Any) -> Array: ...
    def in_dll(cls, dll: _Dll, name: str) -> Array: ...


class PyCPointerType(type):
    def __new__(mcs, *args, **kwargs) -> PyCPointerType: ...
    def __mul__(cls, other: int) -> Array: ...  ## return is PyCArrayType
    def __imul__(cls, other: int) -> Array: ...
    def from_address(cls, value: int) -> CData: ...
    def from_buffer(cls, obj: _Any, offset: int = 0) -> CData: ...
    def from_buffer_copy(cls, obj: _Any, offset: int = 0) -> CData: ...
    def from_param(cls, value: _PyCArg | _Any) -> CData: ...
    def in_dll(cls, dll: _Dll, name: str) -> CData: ...
    def set_type(cls, tp: type) -> None: ...


class PyCStructType(type):
    def __new__(mcs, *args, **kwargs) -> PyCStructType: ...
    def __delattr__(self, item: str) -> None: ...
    def __setattr__(self, key: str, value: _Any) -> None: ...
    def __mul__(cls, other: int) -> Array: ...  ## return is PyCArrayType
    def __imul__(cls, other: int) -> Array: ...
    def from_address(cls, value: int) -> CData: ...
    def from_buffer(cls, obj: _Any, offset: int = 0) -> CData: ...
    def from_buffer_copy(cls, obj: _Any, offset: int = 0) -> CData: ...
    def from_param(cls, value: _PyCArg | _Any) -> CData: ...
    def in_dll(cls, dll: _Dll, name: str) -> CData: ...
    def set_type(cls, tp: type) -> None: ...

