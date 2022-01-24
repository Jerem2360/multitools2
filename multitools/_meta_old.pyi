from dataclasses import dataclass
from typing import Any, Optional
from types import CodeType


@dataclass
class ClassData:
    name: str
    bases: tuple[type]
    abstract: bool
    cls_dict: dict[str, Any]
    superclass: type

    def __repr__(self) -> str: ...


class AbstractMethodDescriptor:
    def __init__(self, function: callable) -> None:
        self.__doc__: str = ...
        self.__name__: str = ...
        self.__qualname__: str = ...
        self.__annotations__: dict = ...
        self.__code__: Optional[CodeType] = ...
        self.__closure__: tuple = ...
        self.__defaults__: tuple[type] = ...
        self.__globals__: dict[str, Any] = ...
        self.__kwdefaults__: dict = ...

    def __call__(self, *args, **kwargs) -> Any: ...
    def __repr__(self) -> str: ...
    def override(self, new_function: callable) -> None: ...
    @property
    def overridden(self) -> bool: ...


class MultiMeta(type):
    # noinspection PyMissingConstructor
    def __init__(cls, name: str, bases: tuple[type], dct: dict[str, Any]) -> None:
        cls.__data__: ClassData = ...
    def __repr__(self) -> str: ...
    def __instancecheck__(cls, instance: object) -> bool: ...
    def __subclasscheck__(cls, subclass: type) -> bool: ...

