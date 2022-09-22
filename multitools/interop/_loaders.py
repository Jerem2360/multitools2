from ctypes import c_void_p as _void_p, cast as _cast
import _ctypes

from ..errors._errors import err_depth, UnresolvedExternalError
from ._func import CFunction
from .._parser import parse_args
from ._base_type import CType


class CallConv(int): ...


class Library:
    _refs = {}

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._handle = 0
        self.__name__ = '<unknown>'
        return self

    def __init__(self, *args, **kwargs):
        raise err_depth(TypeError, f"class {type(self).__name__} cannot be instantiated in that way. Use"
                                   f" {type(self).__name__}.load() instead.")

    def __del__(self):
        try:
            Library._refs[self._handle] -= 1
            if Library._refs[self._handle] <= 0:
                try:
                    _ctypes.FreeLibrary(self._handle)
                except:
                    pass
            del Library._refs[self._handle]
        except:
            pass

    def __getitem__(self, item):
        parse_args((item,), int)
        return self.get_proc(item, mode=0)

    def get_proc(self, name, mode=1, argtypes=..., restype=...):
        _RT = CType | type(Ellipsis) | None
        parse_args((name, mode, argtypes, restype),
                   str | int, int, tuple[_RT, ...] | type(Ellipsis), _RT)
        if self._handle <= 0:
            raise err_depth(ValueError, "NUL pointer reference.", depth=1)

        class _FT(_ctypes.CFuncPtr):
            _flags_ = mode

        try:
            fn = _FT((name, self))
        except AttributeError:
            msg = f"Unknown function '{name}'." if isinstance(name, str) else f"Ordinal {name} ({hex(name)}) not found."
            # noinspection PyExceptionInherit
            raise UnresolvedExternalError(msg, depth=1) from None
        addr = _cast(fn, _void_p).value
        # print(argtypes, restype)
        res = CFunction[argtypes, restype](addr)
        if isinstance(name, str):
            res.__module__ = self.__name__
            res.__name__ = name
        else:
            res.__module__ = self.__name__
            res.__name__ = ':' + str(name)
        return res

    @classmethod
    def load(cls, source, callconv=1):
        parse_args((source, callconv), str, int, depth=1)
        source = source.replace('/', '\\')
        hModule = _ctypes.LoadLibrary(source, callconv)
        lib = cls.__new__(cls)
        lib._handle = hModule
        lib.__name__ = source.split('\\')[-1].rsplit('.', 1)[0]
        if lib._handle not in Library._refs:
            Library._refs[lib._handle] = 0
        Library._refs[lib._handle] += 1
        return lib

    @property
    def handle(self):
        return self._handle

