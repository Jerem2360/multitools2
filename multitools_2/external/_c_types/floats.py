from .base import CType as _Ct

"""
C floating point types.

Matching:

Float -> 'float'
Double -> 'double'
LongDouble -> 'long double'
"""


_FLOAT_SUFFIX = "f"
_DOUBLE_SUFFIX = "d"


class Float(float, metaclass=_Ct):
    base = "float"

    def __repr__(self):
        return repr(self.__handle__.value)

    def __float__(self):
        return self.__handle__.value

    def __str__(self):
        return str(self.__handle__.value) + _FLOAT_SUFFIX

    def __int__(self):
        return int(self.__handle__.value)

    def __bool__(self):
        return self.__handle__.value != 0.0


class Double(float, metaclass=_Ct):
    base = "double"

    def __repr__(self):
        return repr(self.__handle__.value)

    def __float__(self):
        return self.__handle__.value

    def __str__(self):
        return str(self.__handle__.value) + _DOUBLE_SUFFIX

    def __int__(self):
        return int(self.__handle__.value)

    def __bool__(self):
        return self.__handle__.value != 0.0


class LongDouble(float, metaclass=_Ct):
    base = "long double"

    def __repr__(self):
        return repr(self.__handle__.value)

    def __float__(self):
        return self.__handle__.value

    def __str__(self):
        return str(self.__handle__.value) + _DOUBLE_SUFFIX

    def __int__(self):
        return int(self.__handle__.value)

    def __bool__(self):
        return self.__handle__.value != 0.0

