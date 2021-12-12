from typing import Any as _Any, Union as _Union
from types import MethodType as _Method, FunctionType as _Function


_ArgTypes = list[type]
_ArgNames = list[str]
_Restype = type


_Func = _Union[_Function, _Method]


def gather(target: _Union[_Func, type]) -> tuple[_ArgNames, _ArgTypes, _Restype]:
    annot = target.__annotations__
    restype = _Any
    argtypes = []
    argnames = []
    for k in annot:
        argname = k
        argtype = annot[k]
        if argname == 'return':
            restype = argtype
        else:
            argnames.append(argname)
            argtypes.append(argtype)

    return argnames, argtypes, restype

