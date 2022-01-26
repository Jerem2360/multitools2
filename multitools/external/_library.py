from .._meta import *
from .. import system
from .._ref import *
from .._type_check import *
from ._types import *
from ..errors import AccessViolationError, NullReferenceError
import ctypes as _ctype
import os
import _ctypes

NULL = Null()
"""
The C NULL constant.

counts as:
- 0 when converted to int or float
- False when used as a condition
- the null byte when used as bytes

Many arithmetic or function-related operations done on it
will raise NullReferenceError.
"""


class ExternalFunction(metaclass=MultiMeta):
    def __init__(self, funcptr, argtypes, restype):
        typecheck(funcptr, (_ctypes.CFuncPtr,), target_name='funcptr')
        typecheck(argtypes, (tuple,), target_name='argtypes')
        typecheck(restype, (type, type(None)), target_name='restype')
        self._handle = funcptr
        self._restype = None
        self._argtypes = ()
        self.set_restype(restype)
        self.set_argtypes(argtypes)
        self.__name__ = '<undefined>'

    @staticmethod
    def _manage_exception(e: OSError):
        error_text = e.args[0]
        if 'access violation' in error_text:
            error_text = error_text.removeprefix("exception: ")
            error_text = error_text.removeprefix("access violation ")
            error_text = error_text.replace('reading', "Cannot read at")
            error_text = error_text.replace('writing', "Cannot write at")
            raise AccessViolationError(error_text)

        return e

    @staticmethod
    def _manage_builtins(arg):
        if isinstance(arg, str):
            return Str(arg)
        if isinstance(arg, int):
            if arg.bit_length() <= 4:
                return Int(arg)
            if arg.bit_length() <= 8:
                return Long(arg)
            return Long[True, True](arg)

        if isinstance(arg, float):
            int1, int2 = arg.as_integer_ratio()
            length = int1.bit_length() + int2.bit_length()
            del int1, int2
            if length <= 8:
                return Float(arg)
            if length <= 16:
                return Double(arg)
            return Double[True](arg)

        if isinstance(arg, bool):
            return Bool(arg)

        return arg

    def _manage_args(self, args):
        cargs = []
        argno = -1
        for arg in args:
            argno += 1
            if arg == NULL:  # NULL passed as argument
                cargs.append(None)  # ctypes uses None as a NULL reference
                continue

            arg = self._manage_builtins(arg)

            if issubclass(self._argtypes[argno], CType):  # argument must be a c type
                if isinstance(arg, CInstanceType):  # argument is a c instance

                    if isinstance(arg, self._argtypes[argno].__instance_type__):  # c argument of the right type
                        cargs.append(arg.handle)
                        continue
                    # c argument of the wrong type
                    raise TypeError(
                        f"'arg {argno + 1}': expected type "
                        f"'{self._argtypes[argno].__name__}', got "
                        f"'{arg.ctype.__name__}' instead."
                    )
                # not a c argument
                raise TypeError(
                    f"'arg {argno + 1}': expected type "
                    f"'{self._argtypes[argno].__name__}', got "
                    f"'{type(arg).__name__}' instead."
                )
            # no c argument required
            typecheck(arg, (self._argtypes[argno],),
                      target_name=f"arg {argno + 1}")
            cargs.append(arg)
            continue
        return cargs

    def _manage_result(self, result):

        if self._restype is None:  # if no result is expected:
            return None

        if result is None:
            return NULL  # function returned an unexpected NULL reference

        if issubclass(self._restype, CType):  # c type required
            if isinstance(result, self._restype.__c_origin__):  # right ctypes type found
                return self._restype(result)
            # wrong ctype or not a c type
            raise TypeError(
                f"Returned unexpected data: "
                f"Expected type '{self._restype.__name__}'."
            )
        # no c type required
        if not isinstance(result, self._restype):  # type checking for backwards compatibility
            raise TypeError(
                f"Returned unexpected data: "
                f"Expected type '{self._restype.__name__}'."
            )
        return result

    def __call__(self, *args, **kwargs):
        ckwargs = [value for key, value in kwargs.items()]
        cargskwargs = [*self._manage_args(args), *self._manage_args(ckwargs)]

        try:
            cresult = self._handle(*cargskwargs)
        except OSError as e:
            raise self._manage_exception(e)

        return self._manage_result(cresult)

    def set_restype(self, tp):
        typecheck(tp, (type, type(None)), target_name='tp')
        if issubclass(tp, CType):
            self._handle.restype = tp.__c_origin__
            self._restype = tp
            return
        self._handle.restype = self._restype = tp

    def set_argtypes(self, argtypes):
        typecheck(argtypes, (tuple,), target_name='argtypes')
        _builtin_valid = {
            int: int,
            bytes: bytes,
            str: Str,
            float: Float,
            type(None): type(None),
        }
        self._argtypes = []
        cargtypes = []
        for argtp in argtypes:
            typecheck(argtp, (type,), target_name='argtypes', expected_type_name='tuple[type, ...]')
            self._argtypes.append(argtp)
            if issubclass(argtp, CType):
                cargtypes.append(argtp.__c_origin__)
            elif argtp in _builtin_valid:
                cargtypes.append(_builtin_valid[argtp])
            else:
                cargtypes.append(argtp)

        self._handle.argtypes = tuple(cargtypes)


class Library(metaclass=MultiMeta):
    # library loading flags:
    DONT_RESOLVE_DLL_REFERENCES = 0x00000001
    LOAD_IGNORE_CODE_AUTHZ_LEVEL = 0x00000010
    LOAD_LIBRARY_AS_DATAFILE = 0x00000002
    LOAD_LIBRARY_AS_DATAFILE_EXCULSIVE = 0x00000040
    LOAD_LIBRARY_AS_IMAGE_RESOURCE = 0x00000020
    LOAD_LIBRARY_SEARCH_APPLICATION_DIR = 0x00000200
    LOAD_LIBRARY_SEARCH_DEFAULT_DIRS = 0x00001000
    LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR = 0x00000100
    LOAD_LIBRARY_SEARCH_SYSTEM32 = 0x00000800
    LOAD_LIBRARY_SEARCH_USER_DIRS = 0x00000400
    LOAD_WITH_ALTERED_SEARCH_PATH = 0x00000008
    LOAD_LIBRARY_REQUIRE_SIGNED_TARGET = 0x00000080
    LOAD_LIBRARY_SAFE_CURRENT_DIRS = 0x00002000

    # function loading flags:
    cdecl = 0x00000001
    FUNCFLAG_HRESULT = 0x00000002
    FUNCFLAG_PYTHONAPI = 0x00000004
    stdcall = 0x00000000
    FUNCFLAG_USE_ERRNO = 0x00000008
    FUNCFLAG_USE_LASTERROR = 0x00000010

    def __init__(self, library):
        typecheck(library, (system.Library,), target_name='library')
        self._handle = library

    def __getattr__(self, item):
        typecheck(item, (str,))
        return self.load_function(item)

    def __getitem__(self, item):
        typecheck(item, (int,))
        return self.load_function(item)

    def load_function(self, name_or_ordinal, argtypes=(), restype=None, flags=0):
        typecheck(name_or_ordinal, (int, str,), target_name='name | ordinal')
        typecheck(argtypes, (tuple,), target_name='argtypes')
        typecheck(restype, (type, type(None)), target_name='restype')
        typecheck(flags, (int,), target_name='flags')

        funcptr = self._handle.getfunc(name_or_ordinal, flags=flags)
        ext_func = ExternalFunction(funcptr, argtypes, restype)
        if isinstance(name_or_ordinal, str):
            ext_func.__name__ = name_or_ordinal
        return ext_func

    @staticmethod
    def load(library, flags=0):
        typecheck(library, (str,), target_name='library')
        typecheck(flags, (int,), target_name='flags')
        return Library(system.Library.load(library, flags=flags))

    def __repr__(self):
        if self._handle.name != "":
            return f"<external library '{self._handle.name}' at {hex(id(self))}>"
        return f"<external library at {hex(id(self))}>"


