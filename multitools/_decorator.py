from ._meta import *


class Decorator(metaclass=MultiMeta):
    def __new__(cls, func_dec):

        def getargs(*args, **kwargs):
            if (len(args) == 0) and (len(kwargs) == 0):
                return func_dec

            def decorator(func):
                return func_dec(func, *args, **kwargs)
            return decorator

        return getargs

