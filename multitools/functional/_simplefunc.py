from .._meta import *
from .._type_check import typecheck
from .._ref import reference
import types


class SimpleFunction(metaclass=MultiMeta):
    def __init__(self, *args, **kwargs):
        if (len(args) == 1) and (len(kwargs) == 0):
            func = args[0]
            typecheck(func, (types.FunctionType,), target_name="function")
            self._handle = func
        elif (len(args) == 2) and ((len(kwargs) == 0) or ('name' in kwargs) or ('argdefs' in kwargs) or
                                   ('closure' in kwargs)):
            code = args[0]
            glob = args[1]
            name = kwargs.get('name', None)
            argdefs = kwargs.get('argdefs', None)
            closure = kwargs.get('closure', None)

            typecheck(code, (types.CodeType,), target_name="code")
            typecheck(glob, (dict,), target_name="globals")
            typecheck(name, (str, type(None)), target_name="name")
            typecheck(argdefs, (tuple, type(None)), target_name="argdefs")
            typecheck(closure, (tuple, type(None)), target_name="closure")

            self._handle = types.FunctionType(code, glob, name=name, argdefs=argdefs, closure=closure)
        self.__name__ = reference("_handle.__name__", type(self).__name__)
        # noinspection PyTypeChecker
        self.__annotations__ = reference("_handle.__annotations__", {})

    __closure__ = reference("_handle.__closure__", (), writable=False)
    __code__ = reference("_handle.__code__", None)
    __defaults__ = reference("_handle.__defaults__", ())
    __globals__ = reference("_handle.__globals__", {}, writable=False)
    __kwdefaults__ = reference("_handle.__kwdefaults__", {})

