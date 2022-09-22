from ._base_type import  CType as _CType
from .._parser import parse_args
from ..errors._errors import err_depth


from ctypes import c_wchar as _wchar_t


class Byte(_CType):
    __type__ = 'b'
    __c_name__ = 'byte'

    def __init__(self, value):
        parse_args((value,), bytes, depth=1)
        if len(value) != 1:
            raise err_depth(ValueError, "'value' must be a 1-character byte string.", depth=1)
        super().__init__(value)


class UByte(_CType):
    __type__ = 'B'
    __c_name__ = 'unsigned byte'

    def __init__(self, value):
        parse_args((value,), bytes, depth=1)
        if len(value) != 1:
            raise err_depth(ValueError, "'value' must be a 1-character byte string.", depth=1)
        if int(value) < 0:
            raise err_depth(ValueError, "UByte requires a non-negative byte character.", depth=1)
        super().__init__(value)


class Char(_CType):
    __type__ = 'c'
    __c_name__ = 'char'

    def __init__(self, value):
        parse_args((value,), bytes, depth=1)
        if len(value) != 1:
            raise err_depth(ValueError, "'value' must be a 1-character byte string.", depth=1)
        super().__init__(value)


class WChar(_CType):
    # type not supported by the struct module, so we rely on ctypes.c_wchar:
    __type__ = '*'
    __simple__ = _wchar_t
    __c_name__ = 'wchar_t'

    def __init__(self, value):
        parse_args((value,), str, depth=1)
        if len(value) != 1:
            raise err_depth(ValueError, "'value' must be a 1-character unicode string.", depth=1)
        super().__init__(value)

