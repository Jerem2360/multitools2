from ._base import *


class AccessViolationError(CustomException):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, 'multitools', OSError, *args, **kwargs)


class NullReferenceError(CustomException):
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, 'multitools', ReferenceError, *args, **kwargs)

