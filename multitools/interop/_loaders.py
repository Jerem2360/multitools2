from ctypes import c_void_p as _void_p, cast as _cast
import _ctypes

from ..errors._errors import err_depth, UnresolvedExternalError
from ._func import CFunction
from .._parser import parse_args
from ._base_type import CType
from .. import *


class CallConv(int): ...


class Library:
    """
    Type representing a loaded external library.
    Library.load(source, *, callconv) -> loaded external library
    """

    _refs = {}

    def __new__(cls, *args, **kwargs):
        """
        Create and return a new instance.
        Defaults to NULL.
        """
        self = super().__new__(cls)
        self._handle = 0
        self.__name__ = '<NULL>'
        return self

    def __init__(self, *args, **kwargs):
        """
        This class cannot be directly instantiated.
        """
        raise err_depth(TypeError, f"class {type(self).__name__} cannot be instantiated in that way. Use"
                                   f" {type(self).__name__}.load() instead.", depth=1)

    def __del__(self):
        """
        Destructor.
        Frees our library from memory when we no longer need it.
        """
        try:
            Library._refs[self._handle] -= 1
            if Library._refs[self._handle] <= 0:
                try:
                    self.free()
                except:
                    pass
            del Library._refs[self._handle]
        except:
            pass

    def __getitem__(self, item):
        """
        Implement self[ordinal]
        Get a function from a loaded library, given its ordinal.
        """
        parse_args((item,), int)
        return self.get_proc(item, mode=0)

    def free(self):
        """
        Free the memory associated with the library and its dependencies.
        """
        if _MS_WIN32:
            # on Windows, use FreeLibrary():
            # noinspection PyUnresolvedReferences
            _ctypes.FreeLibrary(self._handle)
        else:
            # on posix, use dlclose():
            # noinspection PyUnresolvedReferences
            _ctypes.dlclose(self._handle)

    def get_proc(self, name, /, *, mode=1, argtypes=..., restype=...):
        """
        Get a function from a loaded library, either by ordinal, or by name.
        """
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
        res = CFunction[argtypes, restype](addr, flags=mode)
        if isinstance(name, str):
            res.__module__ = self.__name__
            res.__name__ = name
        else:
            res.__module__ = self.__name__
            res.__name__ = ':' + str(name)
        return res

    @classmethod
    def load(cls, source, *, callconv=1):
        """
        Load an external library into memory and return a reference to it.
        callconv only applies on Windows and specifies the calling convention
        to use when loading symbols from the library. It can be __cdecl or __stdcall.
        """
        parse_args((source, callconv), str, int, depth=1)
        source = source.replace('/', '\\')
        if _MS_WIN32:
            # on Windows, use LoadLibrary()
            # noinspection PyUnresolvedReferences
            hModule = _ctypes.LoadLibrary(source, callconv)
        else:
            # on posix, use dlopen()
            # noinspection PyUnresolvedReferences
            hModule = _ctypes.dlopen(source)
        lib = cls.__new__(cls)
        lib._handle = hModule
        lib.__name__ = source.split('\\')[-1].rsplit('.', 1)[0]
        if lib._handle not in Library._refs:
            Library._refs[lib._handle] = 0
        Library._refs[lib._handle] += 1
        return lib

    @property
    def handle(self):
        """
        A unique integer pointing to the loaded library's data.
        On Windows, this is the HMODULE instance, while on posix,
        this is a pointer to the start of the library's memory.
        """
        return self._handle

