from ._library import ExternalFunction, Library, NULL
from ._types import CType, CInstanceType
from ._types import Int, Long, Short, Size_t, SSize_t
from ._types import Float, Double
from ._types import Bool
from ._types import Str, Char, Bytes
from ._types import Null as NULL_t
from ._types import Ptr as Pointer
from .. import _decorator

from types import FunctionType as _FuncType

__all__ = [
    "NULL",
    "NULL_t",
    "CType",
    "CInstanceType",
    "Int",
    "Long",
    "Short",
    "Size_t",
    "SSize_t",
    "Float",
    "Double",
    "Bool",
    "Str",
    "Char",
    "Bytes",
    "Pointer",
    "ExternalFunction",
    "Library",
    "ctype",
    "DllImport",
]


def ctype(instance: CInstanceType) -> CType:
    return instance.ctype


@_decorator.Decorator
def DllImport(func: _FuncType, dll: str, flags=0, funcflags=0):
    """
    Decorator for quick dll importing.
    Return type and arg types are set based on the annotations given to
    the decorated function.
    Errors are raised if invalid types are used.
    Custom flags can be given for both library loading and function loading.
    """
    lib = Library.load(dll, flags=flags)
    argtypes = []
    restype = None
    for k, v in func.__annotations__.items():
        if k == 'return':
            restype = v
            continue
        argtypes.append(v)

    argtypes = tuple(argtypes)
    func = lib.load_function(func.__name__, argtypes=argtypes, restype=restype, flags=funcflags)
    return func

