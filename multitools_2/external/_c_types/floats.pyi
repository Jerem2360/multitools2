from .base import CType


class Float(float, metaclass=CType):
    base: str = ...

    def __new__(cls, value: float, *args, **kwargs) -> Float: ...
    def __repr__(self) -> str: ...
    def __float__(self) -> float: ...
    def __str__(self) -> str: ...
    def __int__(self) -> int: ...
    def __bool__(self) -> bool: ...


class Double(float, metaclass=CType):
    base: str = ...

    def __new__(cls, value: float, *args, **kwargs) -> Double: ...
    def __repr__(self) -> str: ...
    def __float__(self) -> float: ...
    def __str__(self) -> str: ...
    def __int__(self) -> int: ...
    def __bool__(self) -> bool: ...


class LongDouble(float, metaclass=CType):
    base: str = ...

    def __new__(cls, value: float, *args, **kwargs) -> LongDouble: ...
    def __repr__(self) -> str: ...
    def __float__(self) -> float: ...
    def __str__(self) -> str: ...
    def __int__(self) -> int: ...
    def __bool__(self) -> bool: ...
