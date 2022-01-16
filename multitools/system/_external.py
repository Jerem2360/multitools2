import _ctypes
from .._meta import *
from .._type_check import typecheck


CData = type(getattr(_ctypes, "_SimpleCData"))
CFuncPtr = _ctypes.CFuncPtr
# noinspection PyTypeChecker
PyCFuncPtrType = type(_ctypes.CFuncPtr)
"""meta type for C function pointers"""


class Library(metaclass=MultiMeta):
    """
    Represents a loaded external library.
    """
    def __init__(self, handle):
        """
        Initialize a new already loaded library from it's integer handle.
        """
        typecheck(handle, (int,), target_name="handle")
        self._handle = handle
        self._freed = False

    @staticmethod
    def load(path, flags=0):
        """
        Load and initialize a new Library object from the library's on-disk path, with
        optional flags that default to 0.
        """
        typecheck(path, (str,), target_name="path")
        typecheck(flags, (int, bytes), target_name="flags")
        return Library(_ctypes.LoadLibrary(path, flags))

    def getfunc(self, name_or_ordinal, flags=0):
        """
        Get a function in the library from either a name or an ordinal.
        Returns a callable _ctypes.CFuncPtr object.
        """
        typecheck(name_or_ordinal, (int, bytes, str), target_name="name_or_ordinal")
        typecheck(flags, (int, bytes), target_name="flags")
        if self._freed:
            raise AttributeError("Can't reference a function from an unallocated library.")

        class WrapMeta(type(_ctypes.CFuncPtr)):
            def __repr__(cls):
                if not hasattr(cls, "__wrap_name__"):
                    cls.__wrap_name__ = cls.__name__
                return f"<multitools wrapper class '{cls.__wrap_name__}'>"

        class Wrap(_ctypes.CFuncPtr, metaclass=WrapMeta):
            _flags_ = flags
            __wrap_name__ = "CFuncPtr"

        try:
            result = Wrap((name_or_ordinal, self))
        except AttributeError:
            if isinstance(name_or_ordinal, int):
                raise ReferenceError(f"Library at {self._handle} has no function of ordinal {name_or_ordinal}.")
            else:
                raise NameError(f"Library at {self._handle} has no function named '{name_or_ordinal}'.")
        del Wrap
        del WrapMeta
        return result

    def free(self):
        """
        Free the provided library from memory.
        Once freed, the Library object becomes unusable since
        the library data is no longer in memory.
        """
        _ctypes.FreeLibrary(self._handle)
        self._freed = True

