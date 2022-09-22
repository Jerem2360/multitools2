from ._base_type import CType as _CType
from ..errors._errors import err_depth
from .._parser import parse_args
from ..interface import SupportsIndex, SupportsBool
from .. import *


from ctypes import c_short as _short, c_int as _int, \
    c_long as _long, c_longlong as _longlong, sizeof as _sizeof, \
    c_size_t as _size_t, c_ssize_t as _ssize_t


# integer types' boundary values:
_USHORT_MAX = 2 ** (_sizeof(_short) * 8) - 1
_UINT_MAX = 2 ** (_sizeof(_int) * 8) - 1
_ULONG_MAX = 2 ** (_sizeof(_long) * 8) - 1
_ULONGLONG_MAX = 2 ** (_sizeof(_longlong) * 8) - 1
_SIZE_T_MAX = 2 ** (_sizeof(_size_t) * 8) - 1
_SHORT_MAX = ((_USHORT_MAX + 1) / 2) - 1
_SHORT_MIN = -(_SHORT_MAX + 1)
_INT_MAX = ((_UINT_MAX + 1) / 2) - 1
_INT_MIN = -(_INT_MAX + 1)
_LONG_MAX = ((_ULONG_MAX + 1) / 2) - 1
_LONG_MIN = -(_LONG_MAX + 1)
_LONGLONG_MAX = ((_ULONGLONG_MAX + 1) / 2) - 1
_LONGLONG_MIN = -(_LONGLONG_MAX + 1)
_SSIZE_T_MAX = ((_SIZE_T_MAX + 1) / 2) - 1
_SSIZE_T_MIN = -(_SSIZE_T_MAX + 1)


_OVERFLOW_ERR_STR = "Integer too large to be represented in this format. Boundaries are: {0} <= value <= {1}"

def _check_range(value, min_, max_):
    if not (min_ <= value <= max_):
        raise err_depth(OverflowError, _OVERFLOW_ERR_STR.format(min_, max_), depth=2)


def _make_int(_raw_data):
    return int.from_bytes(_raw_data, _DEFAULT_BYTEORDER)


class Short(_CType):
    __type__ = 'h'
    __c_name__ = 'short'

    def __init__(self, value):
        parse_args((value,), SupportsIndex, depth=1)
        value = value.__index__()
        _check_range(value, _SHORT_MIN, _SHORT_MAX)
        super().__init__(value)

    def __int__(self):
        return _make_int(self._data.view()[:])


class UShort(_CType):
    __type__ = 'H'
    __c_name__ = 'unsigned short'

    def __init__(self, value):
        parse_args((value,), SupportsIndex, depth=1)
        value = value.__index__()
        _check_range(value, 0, _USHORT_MAX)
        super().__init__(value)

    def __int__(self):
        return _make_int(self._data.view()[:])


class Int(_CType):
    __type__ = 'i'
    __c_name__ = 'int'

    def __init__(self, value):
        parse_args((value,), SupportsIndex, depth=1)
        value = value.__index__()
        _check_range(value, _INT_MIN, _INT_MAX)
        super().__init__(value)

    def __int__(self):
        return _make_int(self._data.view()[:])


class UInt(_CType):
    __type__ = 'I'
    __c_name__ = 'unsigned int'

    def __init__(self, value):
        parse_args((value,), SupportsIndex, depth=1)
        value = value.__index__()
        _check_range(value, 0, _UINT_MAX)
        super().__init__(value)

    def __int__(self):
        return _make_int(self._data.view()[:])


class Long(_CType):
    __type__ = 'l'
    __c_name__ = 'long'

    def __init__(self, value):
        parse_args((value,), SupportsIndex, depth=1)
        value = value.__index__()
        _check_range(value, _LONG_MIN, _LONG_MAX)
        super().__init__(value)

    def __int__(self):
        return _make_int(self._data.view()[:])


class ULong(_CType):
    __type__ = 'L'
    __c_name__ = 'unsigned long'

    def __init__(self, value):
        parse_args((value,), SupportsIndex, depth=1)
        value = value.__index__()
        _check_range(value, 0, _ULONG_MAX)

    def __int__(self):
        return _make_int(self._data.view()[:])


class LongLong(_CType):
    __type__ = 'q'
    __c_name__ = 'long long'

    def __init__(self, value):
        parse_args((value,), SupportsIndex, depth=1)
        value = value.__index__()
        _check_range(value, _LONGLONG_MIN, _LONGLONG_MAX)
        super().__init__(value)

    def __int__(self):
        return _make_int(self._data.view()[:])


class ULongLong(_CType):
    __type__ = 'Q'
    __c_name__ = 'unsigned long long'

    def __init__(self, value):
        parse_args((value,), SupportsIndex, depth=1)
        value = value.__index__()
        _check_range(value, 0, _ULONGLONG_MAX)
        super().__init__(value)

    def __int__(self):
        return _make_int(self._data.view()[:])


class Size_t(_CType):
    __type__ = 'N'
    __simple_type__ = 'P'
    __c_name__ = 'size_t'

    def __init__(self, value):
        parse_args((value,), SupportsIndex, depth=1)
        value = value.__index__()
        _check_range(value, 0, _SIZE_T_MAX)
        super().__init__(value)

    def __int__(self):
        return _make_int(self._data.view()[:])


class SSize_t(_CType):
    __type__ = 'n'
    __simple_type__ = 'P'
    __c_name__ = 'Py_ssize_t'  # yes, this is the case, whether you believe it or not

    def __init__(self, value):
        parse_args((value,), SupportsIndex, depth=1)
        value = value.__index__()
        _check_range(value, _SSIZE_T_MIN, _SSIZE_T_MAX)
        super().__init__(value)

    def __int__(self):
        return _make_int(self._data.view()[:])


class Bool(_CType):
    __type__ = '?'
    __c_name__ = 'bool'

    def __init__(self, value):
        parse_args((value,), SupportsBool, depth=1)
        value = bool(value)
        super().__init__(value)

    def __int__(self):
        return _make_int(self._data.view()[:])

    def __bool__(self):
        return bool(int(self))

