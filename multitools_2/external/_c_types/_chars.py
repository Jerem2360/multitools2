from ._base import CType as _Ct
from .._r import type_check as _tp_check


class Byte(bytes, metaclass=_Ct):
    base = "byte"

    def __new__(cls, value, *args, **kwargs):
        if value == 0:
            value = b'\x00'
        _tp_check((value,), bytes)
        if len(value) != 1:
            raise ValueError("Byte chars must have a length of 1.")
        return super().__new__(cls, value)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"b'\\x{self.hex()}'"


class UByte(bytes, metaclass=_Ct):
    base = "ubyte"

    def __new__(cls, value, *args, **kwargs):
        if value == 0:
            value = b'\x00'
        _tp_check((value,), bytes)
        if len(value) != 1:
            raise ValueError("Byte chars must have a length of 1.")
        return super().__new__(cls, value)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"b'\\x{self.hex()}'"


class Char(str, metaclass=_Ct):
    base = "char"

    def __new__(cls, value, *args, **kwargs):
        if value == 0:
            value = b'\x00'
        _tp_check((value,), (str, bytes))
        if len(value) != 1:
            raise ValueError("Chars must have a length of 1.")
        if isinstance(value, bytes):
            return super().__new__(cls, str(value, encoding="utf-8"))
        return super().__new__(cls, value)

    def to_c(self):
        # noinspection PyArgumentList
        return self.__c_base__(bytes(self, encoding="utf-8"))

    @classmethod
    def from_c(cls, cval):
        if isinstance(cval, bytes):
            return Char(cval)
        return Char(cval.value)


class WideChar(str, metaclass=_Ct):
    base = "wchar"

    def __new__(cls, value, *args, **kwargs):
        if value == 0:
            value = '\x00'
        _tp_check((value,), str)
        if len(value) != 1:
            raise ValueError("Unicode chars must have a length of 1.")
        return super().__new__(cls, value)


