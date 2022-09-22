from ctypes import c_longdouble as _longdouble

from ._base_type import CType as _CType
from .._parser import parse_args
from ..interface import SupportsFloat


def _parse_float(value, depth=0):
    parse_args((value,), SupportsFloat, depth=depth+1)
    return float(value)


class Float(_CType):
    __type__ = "f"
    __c_name__ = 'float'

    def __init__(self, value):
        value = _parse_float(value, depth=1)
        super().__init__(value)


class Double(_CType):
    __type__ = 'd'
    __c_name__ = 'double'

    def __init__(self, value):
        value = _parse_float(value, depth=1)
        super().__init__(value)


class LongDouble(_CType):
    # this type is not supported by the struct module, so we rely on ctypes.c_longdouble:
    __simple__ = _longdouble
    __type__ = '*'
    __c_name__ = 'long double'

    def __init__(self, value):
        value = _parse_float(value, depth=1)
        super().__init__(value)

