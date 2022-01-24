from ._adminfunc import needs_admin

from .._meta import *
from .._decorator import Decorator as _Dec

from types import FunctionType as _FuncType

__all__ = [
    "needs_admin",
    "Decorator",
]


class Decorator(metaclass=MultiMeta):
    """
    @Decorator
    def f(func, *args, **kwargs) -> Any: ...

    Decorate a function to make it a Decorator object
    A Decorator object is like a builtin decorator, except it can
    accept arguments on decoration.

    'func' is the function decorated by the decorator

    More arguments can be passed in during decoration and
    are effectively passed in to the decorator if required.

    "@decorator()" and "@decorator" will do the same thing.
    """
    def __new__(cls, dec: _FuncType) -> _FuncType:
        return _Dec(dec)

