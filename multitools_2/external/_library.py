import _ctypes
import ctypes
import ctypes as _ct

from .._errors import *
from .._const import *
from .._typing import type_check as _tp_check
from .._meta import MultiMeta as _Mt
from ._c_types import CType as _Ct
from ._pointer import Pointer as _Ptr
from ._array import Array as _Arr


_CData = _ct.c_int.__mro__[-2]  # _ctypes._CData


class ExternalFunction(metaclass=_Mt):
    def __init__(self, funcptr_raw, *args, argtypes=(), restype=None, **kwargs):
        _tp_check((funcptr_raw, argtypes, restype), _ctypes.CFuncPtr, tuple, (type, None))
        if not isinstance(restype, (_Ct, type(None), type(_CData))) and restype not in (_Ptr, int, bytes) and not issubclass(restype, _Ptr):
            raise TypeError(f"Expected type 'CType | type[Pointer] | NoneType | type[int] | type[bytes] | _ctypes.PyCSimpleType', got '{type(restype).__name__}' instead.")

        for argtp in argtypes:
            if not isinstance(argtp, (_Ct, type(None), type(_CData))) and argtp not in (_Arr, _Ptr, int, bytes) and not issubclass(restype, (_Arr, _Ptr)):
                raise TypeError(f"Expected type 'CType | type[Pointer] | type[Array] | NoneType | type[int] | type[bytes] | _ctypes.PyCSimpleType', got '{type(restype).__name__}' instead.")

        self.__handle__ = funcptr_raw
        self._argtypes = argtypes
        self._restype = restype

    def __call__(self, *args):
        c_args = []
        for i in range(len(args)):
            if (not isinstance(type(args[i]), _Ct)) and (not isinstance(args[i], (_CData, _Ptr, int, bytes))):
                raise TypeError("External call arguments must be C types.")
            _tp_check((args[i],), self._argtypes[i])
            c_args.append(args[i].to_c())

        res = self.__handle__(*c_args)
        if self._restype is None:
            return

        if (self._restype is _Arr) or issubclass(self._restype, _Arr):
            if not hasattr(res, '__len__'):
                raise TypeError("Got unexpected data type in return.")
            # noinspection PyTypeChecker
            ArrTp: type[_ct.Array] = self._restype.__type__.__c_base__ * len(res)
            if not isinstance(res, ArrTp):
                raise TypeError("Got unexpected data type in return.")
            return self._restype.from_c(res)

        if (self._restype is _Ptr) or issubclass(self._restype, _Ptr):
            # noinspection PyTypeChecker
            if not isinstance(res, _ct.POINTER(self._restype.__type__.__c_base__)):
                raise TypeError("Got unexpected data type in return.")
            return _Ptr[self._restype.__type__](ctypes.addressof(res.contents))

        if isinstance(self._restype, _Ct):
            if isinstance(res, self._restype.__base__):
                return self._restype(res)
            if not isinstance(res, self._restype.__c_base__):
                raise TypeError("Got unexpected data type in return.")
            return self._restype.from_c(res)

        if issubclass(self._restype, _CData):
            if not isinstance(res, self._restype):
                raise TypeError("Got unexpected data type in return.")
            return res

        if self._restype in (bytes, int):
            if not isinstance(res, self._restype):
                raise TypeError("Got unexpected data type in return.")
            return res

        raise TypeError("Got unexpected data type in return.")

    def __repr__(self):
        ptr = _ct.cast(self.__handle__, _ct.c_void_p)
        return f"<extern function at {hex(ptr.value)}>"


class Library(type(_ctypes), metaclass=_Mt):
    def __init__(self, handle, modname):
        _tp_check((handle, modname), int, str)
        self.__handle__ = handle
        super().__init__(modname)

    def reference(self, name_or_ordinal, argtypes=None, restype=None, flags=0):
        _tp_check((name_or_ordinal, argtypes, restype, flags), (int, str), (tuple[type, ...], None), (type, None), int)

        class FuncPtr(_ctypes.CFuncPtr):
            _flags_ = flags

        class Lib:
            def __init__(_self):
                _self._handle = self.__handle__
        try:
            f = FuncPtr((name_or_ordinal, Lib()))

            if argtypes is not None:
                argtypes_c = []
                for argtp in argtypes:
                    if isinstance(argtp, _Ct):
                        argtypes_c.append(argtp.__c_base__)
                    elif issubclass(argtp, _Arr) or argtp is _Arr:
                        argtypes_c.append(argtp.__type__.__c_base__ * len(argtp))
                    elif issubclass(argtp, _Ptr) or argtp is _Ptr:
                        # noinspection PyTypeChecker
                        argtypes_c.append(_ct.POINTER(argtp.__type__.__c_base__))
                    elif issubclass(argtp, (int, bytes, _CData)) or (argtp in (int, bytes)):
                        argtypes_c.append(argtp)
                    else:
                        raise TypeError("Argument types must be C types, 'bytes', 'int' or their subtypes.")
                f.argtypes = tuple(argtypes_c)
            else:
                argtypes = ()
                f.argtypes = ()

            if restype is not None:
                if isinstance(restype, _Ct):
                    f.restype = restype.__c_base__
                elif issubclass(restype, _Arr) or restype is _Arr:
                    f.restype = restype.__type__.__c_base__ * len(restype)
                elif issubclass(restype, _Ptr) or restype is _Ptr:
                    # noinspection PyTypeChecker
                    f.restype = _ct.POINTER(restype.__type__.__c_base__)
                elif issubclass(restype, (_CData, int, bytes)) or (restype in (int, bytes)):
                    f.restype = restype
                else:
                    raise TypeError("Return type must be a C type, 'bytes', 'int' or one of their subtypes.")
            else:
                f.restype = None
            return ExternalFunction(f, argtypes=argtypes, restype=restype)
        except AttributeError:
            pass
        if isinstance(name_or_ordinal, int):
            msg = f"Library '{self.__name__}' has no function of ordinal {name_or_ordinal}."
        else:
            msg = f"Library '{self.__name__}' has no function named '{name_or_ordinal}'."
        raise ExternalReferenceError(msg)

    def __getattr__(self, item):
        _tp_check((item,), str)
        try:
            return super().__getattribute__(item)
        except AttributeError:
            pass
        if item.startswith('__') and item.endswith('__'):
            raise latest()
        return self.reference(item, flags=1)  # defaults to __cdecl

    def __getitem__(self, args):
        """
        Library[name: str, callconv: Optional[int]] -> ExternalFunction
        """
        _tp_check((args,), (tuple[str, int], str))
        if isinstance(args, tuple):
            if len(args) == 2:
                return self.reference(args[0], flags=args[1])
            if len(args) == 0:
                raise ValueError("Library[...] Missing required 'name' argument. See documentation for more info.")
            return self.reference(args[0], flags=1)
        return self.reference(args, flags=1)

    def __repr__(self):
        return f"<extern module '{self.__name__}'>"

    @staticmethod
    def load(path, flags=0):
        _tp_check((path, flags), str, int)
        name = path.split(STD_PATHSEP)[-1] if STD_PATHSEP in path else path
        try:
            return Library(_ctypes.LoadLibrary(path, flags), name)
        except FileNotFoundError:
            raise FileNotFoundError(f"Unknown library file '{path}'.")

