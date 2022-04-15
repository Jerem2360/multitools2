from .base import CType as _Ct

from .._r import type_check as _tp_check


"""
The C boolean type.
Matches 'bool' in C++, and 'int' in C.
"""


class Bool(int, metaclass=_Ct):
    base = "bool"

    def __new__(cls, value, *args, **kwargs):
        if value == 0:
            value = False
        _tp_check((value,), bool)
        return cls.create_instance(int(value))

    def __repr__(self):
        return repr(bool(self)).lower()

    def __bool__(self):
        return self.__handle__.value

    def __int__(self):
        return int(self.__handle__.value)

