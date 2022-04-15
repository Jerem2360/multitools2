import sys

from .base import CType as _Ct
from .._r import type_check as _tp_check

"""
C character types.

Matching:

Byte -> 'char'
UByte -> 'unsigned char'
Char -> 'char'
WideChar -> '_wchar_t'
"""

_NULL_BYTE = b'\x00'
_NULL_CHAR = '\x00'
_ENCODING = sys.getdefaultencoding()
_WCHAR_STR = "L'{0}'"


class Byte(bytes, metaclass=_Ct):
    base = "byte"

    def __new__(cls, value, *args, **kwargs):
        if value == 0:
            value = _NULL_BYTE
        _tp_check((value,), bytes)
        if len(value) != 1:
            raise ValueError("Byte chars must have a length of 1.")
        return cls.create_instance(value)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"b'\\x{self.hex()}'"

    def __bytes__(self):
        return self.__handle__.value


class UByte(bytes, metaclass=_Ct):
    base = "unsigned byte"

    def __new__(cls, value, *args, **kwargs):
        if value == 0:
            value = _NULL_BYTE
        _tp_check((value,), bytes)
        if len(value) != 1:
            raise ValueError("Byte chars must have a length of 1.")
        return cls.create_instance(value)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"b'\\x{self.hex()}'"

    def __bytes__(self):
        return self.__handle__.value


class Char(str, metaclass=_Ct):
    base = "char"

    def __new__(cls, value, *args, **kwargs):
        if value == 0:
            value = _NULL_BYTE
        _tp_check((value,), (str, bytes))
        if len(value) != 1:
            raise ValueError("Chars must have a length of 1.")
        if isinstance(value, bytes):
            return cls.create_instance(value, encoding=_ENCODING)
        return cls.create_instance(bytes(value, encoding=_ENCODING))

    def __str__(self):
        return str(self.__handle__.value, encoding=_ENCODING)

    def __bytes__(self):
        return self.__handle__.value

    def __repr__(self):
        return "'" + self.__str__() + "'"


class WideChar(str, metaclass=_Ct):
    base = "wchar"

    def __new__(cls, value, *args, **kwargs):
        if value == 0:
            value = _NULL_CHAR
        _tp_check((value,), str)
        if len(value) != 1:
            raise ValueError("Unicode chars must have a length of 1.")
        return cls.create_instance(value)

    def __str__(self):
        return self.__handle__.value

    def __repr__(self):
        return _WCHAR_STR.format(self.__handle__.value)

    def __bytes__(self):
        return bytes(self.__handle__.value, encoding=_ENCODING)

