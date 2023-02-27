import _ctypes

from . import *
from . import _dllimport


"""
The µ character will serve as a place holder for hidden attributes
"""


if MS_WIN64 or MS_WIN32:
    from ._dllimport_win import make_resource as _make_resource, DllHandle
else:
    from ._dllimport_posix import make_resource as _make_resource, DllHandle


def dlopen(name, flags):
    """
    Load a library file into memory.
    Return None if the library cannot be found.
    """
    return DllHandle.open(name, flags)


def dlclose(dl: DllHandle):
    """
    Free a library from memory.
    """
    dl.release()


def dlsym(dl: DllHandle, sym):
    """
    Fetch a symbol from a loaded library.
    Return None if the symbol cannot be found.
    """
    sym = _make_resource(sym)
    if sym is None:
        return
    return dl.symbol(sym)


def call_function(funcptr, args, kwargs, argtypes, restype, paramflags, funcflags, func_obj, errcheck=lambda result, func, args: result):
    real_argtypes = []
    for at in argtypes:
        if at is None:
            real_argtypes.append(None)
        else:
            real_argtypes.append(_dllimport.typelist[at])

    real_restype = None if restype is None else _dllimport.typelist[restype]


    class Proto(_ctypes.CFuncPtr):
        _argtypes_ = real_argtypes
        _restype_ = real_restype
        _flags_ = funcflags
        _errcheck_ = errcheck  # errcheck(result, func, args)
        _paramflags_ = paramflags

    func = Proto(funcptr)

    c_args = []
    c_kwargs = {}

    for arg in args:
        c_args.append(arg.__cparam__)
    for k, v in kwargs.items():
        c_kwargs[k] = v.__cparam__

    func(*c_args, **c_kwargs)


class CParam:
    __slots__ = [
        '_as_parameter_',
        '_keep',
    ]

    def __init__(self, struct_type, value, _keep=None):
        ctypes_t = _dllimport.typelist[struct_type]
        self._as_parameter_ = ctypes_t.from_param(value)
        self._keep = _keep


