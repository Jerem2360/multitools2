import sys

from ._const import *


def get_last_error():
    EType = sys.exc_info()[0]
    eargs = sys.exc_info()[1].args
    return EType(*eargs)


class CustomError(Exception):
    __ename__ = None

    def __new__(cls, *args, **kwargs) -> BaseException:
        etype = kwargs.get('etype', BaseException)
        ename = cls.__ename__ if cls.__ename__ is not None else cls.__name__
        ErrType = type(ename, (etype,), {'args': args})
        ErrType.__module__ = kwargs.get('path', NO_MODULE)
        return ErrType(*args)


class ThreadStateError(CustomError):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, *args, etype=RuntimeError)

