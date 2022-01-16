from typing import Generic, TypeVar, Any
from ._meta import *
import types


_T = TypeVar("_T")


class reference(Generic[_T], _T, metaclass=MultiMeta):
    # actually, this is a function so that the parent class can be set dynamically
    def __init__(self, target_name: str, default: _T, writable: bool = ...) -> None: ...
    def __get__(self, instance: Any, owner: type) -> _T: ...
    def __set__(self, instance: Any, value: _T) -> None: ...
    def __repr__(self) -> str: ...




