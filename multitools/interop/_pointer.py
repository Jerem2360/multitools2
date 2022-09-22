import ctypes
from ctypes import c_void_p as _void_p, POINTER as _PTR, sizeof as _sizeof, c_longlong as _longlong, \
    cast as _cast, py_object as _py_obj, c_char_p as _char_p, c_wchar_p as _wchar_p

import _ctypes

from ._base_type import CType as _CType, CTypeMeta as _CTypeMeta, NULL as _NULL
from ..errors._errors import err_depth
from .._meta import generic
from .._parser import parse_args
from ._mem import Memory
from .._typeshed import *
from .. import *


_ULONGLONG_MAX = 2 ** (_sizeof(_longlong) * 8) - 1


_OVERFLOW_ERR_STR = "Integer too large to be represented in this format. Boundaries are: {0} <= value <= {1}"


def _check_range(value, min_, max_):
    if not (min_ <= value <= max_):
        raise err_depth(OverflowError, _OVERFLOW_ERR_STR.format(min_, max_), depth=2)


class PointerType(_CTypeMeta):
    """
    Metatype for pointer types.
    """
    def __new__(mcs, name, bases, np, ptype=None, **kwargs):
        np['__type__'] = 'P'  # struct format for pointer is 'P'
        cls = super().__new__(mcs, name, bases, np, **kwargs)
        cls.__p_type__ = ptype
        cls.__name__ = (cls.__p_type__.__name__ if cls.__p_type__ is not None else 'void') + '*'
        # print(cls)
        return cls

    @property
    def type(cls):
        return cls.__p_type__

    @property
    def __simple__(cls):
        if cls.__p_type__ is None:
            return _void_p
        try:
            return _PTR(cls.__p_type__.__simple__)
        except:
            return _void_p

    def __instancecheck__(cls, instance):
        if isinstance(type(instance), PointerType) and cls.__p_type__ is None:
            return True
        return super().__instancecheck__(instance)

    def __repr__(cls):
        return f"<C type '{cls.__name__.split('[')[0]}'>"


@generic(_CTypeMeta | None)  # same as @generic(type[CType] | None)
class Pointer(_CType, metaclass=PointerType):
    """
    Pointers to C variables.
    """
    def __init__(self, value):
        """
        Initialize a new Pointer object from an integer address.
        """
        parse_args((value,), int, depth=1)
        _check_range(value, 0, _ULONGLONG_MAX)
        super(type(self), self).__init__(value)
        self._addr = value

    def __eq__(self, other):
        """
        Implement self == other
        Pointer(0) == NULL -> True
        """
        if (other is _NULL) and (self._addr == 0):
            return True
        return super().__eq__(other)

    def __int__(self):
        return int.from_bytes(self._data.view()[:], _DEFAULT_BYTEORDER)

    def __index__(self):
        return int(self)

    def __repr__(self):
        first = super(type(self), self).__repr__().split('[', 1)[0]
        first += f"({int(self)})>"
        return first

    @classmethod
    def __template__(cls, tp):
        """
        Implement cls[*args]
        """
        # here, tp is guaranteed to be a type, as specified by
        # the @generic() declaration.

        # no need to cache the pointer types, this is done by MultiMeta:
        res = cls.dup_shallow()
        res.__p_type__ = tp
        res.__name__ = tp.__name__ + '*'
        return res

    @property
    def contents(self):
        """
        Return the data the pointer points to by de-referencing it.
        Raise TypeError for void and NULL pointers.

        Warning: this may cause access violation if not used correctly.
        """
        if type(self).__p_type__ is None:
            raise err_depth(TypeError, "void pointers cannot be de-referenced.", depth=1)

        if self._addr == 0:
            raise err_depth(TypeError, "NULL pointer.", depth=1)

        ct_v = type(self).__p_type__.__simple__.from_address(self._addr)
        inst = type(self).__p_type__.__new__()
        inst._data = Memory(ct_v)
        return inst

    def to_py(self):
        """
        Convert the pointer to a python object.
        In most cases, this returns the address
        to which the pointer points, in form of a
        python integer.
        However, for these specific types, it returns
        a special value:

        Pointer[PyObject].to_py() -> the actual object the pointer refers to
        Pointer[PyTypeObject].to_py() -> the actual type object the pointer refers to
        Pointer[Char].to_py() -> a python byte-string representing the contents of the C string.
        Pointer[WChar].to_py() -> a python unicode-string representing the contents of the C unicode string.
        Pointer.to_py() -> the address the pointer points to.
        """
        if hasattr(type(type(self).__p_type__), '_special'):
            if type(type(self).__p_type__)._special in (object, type):
                return _cast(self._addr, _py_obj).value
            if type(type(self).__p_type__)._special is str:
                return _cast(self._addr, _wchar_p).value
            if type(type(self).__p_type__)._special is bytes:
                return _cast(self._addr, _char_p).value
        return self._addr

    @classmethod
    def __from_ctypes__(cls, *values):
        ob = values[0]
        parse_args((ob,), (int, _void_p, _char_p, _wchar_p, _ctypes._Pointer))
        addr = (ctypes.cast(ob, _void_p) if not isinstance(ob, _void_p) else ob).value
        return cls(addr)


# register plain Pointer as being the same as Pointer[None] :
Pointer._register_typ_cache((None,), Pointer)

