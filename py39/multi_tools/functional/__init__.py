from dataclasses import dataclass
from ..errors import *


EMPTY_CODE = b"\x64\x00\x53\x00"
EMPTY_COMMENTED_CODE = b"\x64\x01\x53\x00"

def _e(*args, **kwargs):
    pass


EMPTY_FUNCTION = _e


class _ResultTypeReturn:
    def __init__(self, value: bool, exc_info):
        self.__value = value
        self.__exc_info = exc_info

    def __bool__(self):
        return self.__value

    info = property(lambda self: self.__exc_info)


class _ResultType:
    def __init__(self, value: bool):
        self.__value = value

    def __bool__(self):
        return self.__value

    def __call__(self, *exc_info):
        return _ResultTypeReturn(self.__value, exc_info)


Failure = _ResultType(False)
Success = _ResultType(True)


def abstractmethod(func):

    def wrapper(*args, **kwargs):
        raise TypeError(f"Abstract method '{func.__qualname__}' was not implemented.")

    if hasattr(func, '__code__'):
        if (func.__code__.co_code == EMPTY_CODE) or (func.__code__.co_code == EMPTY_COMMENTED_CODE):
            func.__code__ = wrapper.__code__

            return func
        raise ValueError("Abstract methods cannot define a body.")
    raise SimpleTypeError(type(func), "function", "method", "classmethod", "staticmethod")

