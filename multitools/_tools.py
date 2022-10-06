import os.path
import sys

from ._typeshed import *
from .errors._errors import err_depth, NOT_CALLABLE_ERR_STR, ATTR_ERR_STR

"""
"""
"""
stub ideas:

_AnyFunc = TypeVar("_AnyFunc", bound=Callable[[...], Any])  # (...) -> Any
_DecoratorFunc = TypeVar("_DecoratorFunc", bound=Callable[[_AnyFunc, ...], Any])
_Decoration = TypeVar("_Decoration", bound=Callable[[_AnyFunc], Any])  # (Function) -> Any

class Decorator:
    def __init__(self, target: _DecoratorFunc) -> None:
        self.__func__: _DecoratorFunc = ...
        self.__name__: str = ...
        # function attributes
        # ...
        
    def __call__(self, *args, **kwargs) -> _Decoration: ...
    def __getattr__(self, name: str) -> Any: ...
    
"""


class Decorator:
    """
    Simple decorator type. Allows to be called using @decorator(*args, **kwargs) def fn(...): ...
    arguments are passed in to decorators as so:
    decorator(fn, *args, **kwargs)
    In consequence, calling just decorator(*args, **kwargs) would yield a function accepting
    the decorated function as first argument. This is called a Decoration function.

    Decorator(func: Function) -> new decorator
    @decorator(...) def fn(): ... -> func(fn, ...)
    """
    def __init__(self, func):
        if not callable(func):
            raise err_depth(ValueError, NOT_CALLABLE_ERR_STR.format(type(func).__name__))
        self.__func__ = func

    def __call__(self, *args, **kwargs):
        def _inner(fn):
            return self.__func__(fn, *args, **kwargs)

        _inner.__name__ = f"{self.__func__.__name__}.decoration"
        _inner.__module__ = self.__func__.__module__
        _inner.__qualname__ = self.__func__.__qualname__ + '.decoration'
        return _inner

    def __getattr__(self, item):
        if hasattr(self.__func__, item):
            return getattr(self.__func__, item)
        raise err_depth(TypeError, ATTR_ERR_STR.format(type(self).__name__, item), depth=1)


def _branchless_condition(condition, if_true, if_false=None):
    """
    Tool for branchless programming. Note that everything that is passed in
    here is evaluated and potentially called, no matter what is condition.
    Only the result of this function depends on the condition.
    """
    condition = bool(condition)
    if_true = bool(if_true)
    if_false = bool(if_false)
    return condition * if_true + (not condition) * if_false


def _update_path_to_cwd():
    """
    Add the current working directory to sys.path. This is automatically done
    at the start of the interpreter, but never occurs when changing os.curdir
    at runtime.
    """
    sys.path.append(os.path.realpath('.'))

