from typing import Any as _Any, TypeVar as _TypeVar, overload as _overload, Callable as _Callable

from .._ct_secrets import SimpleCData as _SimpleCData


class CType(type):

    def __class_getitem__(mcs, item: type) -> type: ...
    @_overload
    def create_instance(cls, value: _Any, *args, **kwargs) -> _Any: ...
    @_overload
    def create_instance(cls, handle: _SimpleCData, *args, **kwargs) -> _Any: ...
    def __new__(mcs, name: str, bases: tuple[type, ...], np: dict[str, _Any]) -> CType: ...
    def __init__(cls, *args, **kwargs) -> None:
        cls.__handle__: _SimpleCData = ...
        cls.base: str = ...
        cls.__c_base__: type[_SimpleCData] = ...
        cls.__size__: int = ...
        cls.to_c: _Callable[[], _SimpleCData] = ...
        cls.from_c: _Callable[[_SimpleCData], _Any] = ...
        cls.raw: _Callable[[], _Any] = ...

