import ctypes
import struct

import _ctypes
from ctypes import c_void_p as _void_p

from ._base_type import CType, CTypeMeta, NULL
from .._meta import generic
from .._typeshed import *
from ..errors._errors import err_depth
from .._parser import parse_args
from .._tools import _branchless_condition
from .._singleton import singleton

from _ctypes import CFuncPtr as _CFuncPtr


AnyType = singleton("AnyType", __name__)


def _errcheck(res, fn, args):
    return res


def _call_fn_at_address(address, sig, flags, *args, **kwargs):
    argtypes, restype = sig
    print(argtypes, '\n', args)

    if argtypes is Ellipsis:
        class _FT(_ctypes.CFuncPtr):
            _flags_ = flags
        fn = ctypes.cast(address, _FT)
        fn.argtypes = None
    else:
        fn = ctypes.cast(address, ctypes.CFUNCTYPE(_get_ct_type(restype), *(_get_ct_type(a) for a in argtypes)))
    fn.errcheck = _errcheck
    ct_args = tuple(_make_ctypes_arg(arg) for arg in args)
    ct_kwargs = {k: _make_ctypes_arg(v) for k, v in kwargs.items()}
    #
    # (ct_args, ct_kwargs)
    try:
        res = fn(*ct_args, **ct_kwargs)
    except ctypes.ArgumentError as e:
        # print(*e.args)
        raise err_depth(TypeError, "Invalid argument type(s).", depth=2) from None
    if _get_ct_type(restype) is None:
        return
    if isinstance(res, CData):
        return restype.__from_ctypes__(res)
    try:
        res = res if isinstance(res, tuple) else (res,)
        return restype(*res)
    except ValueError or AttributeError:
        raise err_depth(TypeError, "Received data of an unexpected type.", depth=2)


def _make_ctypes_arg(arg):
    # print(type(arg).__bases__)
    if isinstance(arg, CType):
        return arg.__to_ctypes__()
    return arg


def _get_ct_type(arg):
    if arg in (Ellipsis, AnyType, None):
        return None
    if not hasattr(arg, '__simple__'):
        # print(arg, arg.__simple__)
        raise err_depth(TypeError, f"Type '{type(arg)}' cannot be inside the signature of an external function.", depth=2)
    if not isinstance(arg, CTypeMeta):
        raise err_depth(TypeError, "Unable to convert this type to valid C data.", depth=2)
    return arg.__simple__


def _res_from_ctypes(arg, tp):
    # print(arg, tp)
    if tp is Ellipsis:
        return arg.value if isinstance(arg, SimpleCData) else arg
    if isinstance(arg, CData):
        return tp.__from_ctypes__(arg)
    return tp(arg)


def _get_fn_handle(name, source_handle, argtypes, restype):
    class _FuncPtrType(_CFuncPtr):
        _argtypes_ = argtypes
        _restype_ = restype

    class _Dll:
        def __init__(self, handle):
            self._handle = handle

    fn = _FuncPtrType((name, _Dll(source_handle)))
    fn.argtypes = argtypes
    fn.restype = restype
    return fn


class _CFunctionMeta(CTypeMeta):
    def __new__(mcs, name, bases, np, signature=(..., ...), **kwargs):
        # signature = ([arg_t1, arg_t2, ...], res_t)
        parse_args((signature,), tuple[type(Ellipsis) | list[CTypeMeta | type(Ellipsis)], type(Ellipsis) | CTypeMeta], depth=1)
        argtypes = (Ellipsis,) if signature[0] is Ellipsis else signature[0]
        restype = signature[1]
        if restype is Ellipsis:
            restype = AnyType
        cls = super().__new__(mcs, name, bases, np, **kwargs)
        cls._argtypes = argtypes
        cls._restype = restype
        return cls

    def __instancecheck__(cls, instance):
        res = super().__instancecheck__(instance)
        return bool(_branchless_condition(res, res, isinstance(type(instance), _CFunctionMeta)))


@generic(tuple[CType | type(Ellipsis) | None, ...], CType | type(Ellipsis) | None)
class CFunction(CType, metaclass=_CFunctionMeta):
    """
    Pointer to a C function. Template arguments are the same as for typing.Callable,
    except all provided types must be C types.
    Note that @dllimport functions MUST include argument types and return type
    in their declaration.
    """

    __type__ = 'P'

    def __new__(cls, *args, **kwargs):
        self = super(cls, cls).__new__(cls, 0)
        self._address = 0
        self._signature = (..., ...)
        self.__module__ = '<external>'
        self.__qualname__ = "<external>::<unknown>"
        self.__name__ = '<unknown>'
        self.__owner__ = None
        return self

    def __init__(self, *args, **kwargs):
        if len(args) < 1:
            return
        if len(args) > 2:
            return
        if len(args) == 2:
            self.__owner__ = args[1]
            self.__module__ = self.__owner__.__name__
        parse_args((args[0],), int, depth=1)
        self._address = args[0]
        super(type(self), self).__init__(args[0])
        self._data.view()[:] = struct.pack('P', args[0])
        self._flags = int(kwargs.get('flags', 0))

    def __call__(self, *args, **kwargs):
        if self._address <= 0:
            raise err_depth(ValueError, "NUL pointer reference.", depth=1)
        res = _call_fn_at_address(self._address, (type(self)._argtypes, type(self)._restype), self._flags, *args, **kwargs)
        if type(self)._restype is None:
            return
        return res

    def __setattr__(self, key, value):
        if key == '__name__':
            if isinstance(value, str):
                # print(self.__module__, value, key)
                if value.startswith(':'):
                    super(type(self), self).__setattr__('__qualname__', self.__module__ + value)
                else:
                    # print('funcname', self.__module__, value, key)
                    super(type(self), self).__setattr__('__qualname__', self.__module__ + '::' + value)
                    # print('->', self.__qualname__)
            return super(type(self), self).__setattr__(key, value)
        return super(type(self), self).__setattr__(key, value)

    def __repr__(self):
        return f"<function '{self.__qualname__}'>"

    def __eq__(self, other):
        if other is NULL and self._address <= 0:
            return True
        return super(type(self), self).__eq__(other)

    @classmethod
    def __template__(cls, argtypes, restype):
        res = cls.dup_shallow()
        res._argtypes = argtypes
        res._restype = restype
        return res

