from .base import CType as _Ct
from .._r import type_check as _tp_check

"""
C integer types.

Matching:

Short -> 'short'
UShort -> 'unsigned short'
Long -> 'long'
ULong -> 'unsigned long'
Int -> 'int'
UInt -> 'unsigned int'
LongLong -> 'long long'
ULongLong -> 'unsigned long long'


Whilst creating C integer instances, if too big values are passed in,
MemoryError is raised.
"""


class Short(int, metaclass=_Ct):
    base = "short"

    def __new__(cls, value, *args, **kwargs):
        _tp_check((value,), int)
        size = int(value.bit_length() / 8)
        if size > cls.__size__:
            raise MemoryError(f"Too big integer value: expected {cls.__size__} bytes max, but got {size}.")
        return cls.create_instance(value, *args, **kwargs)

    def __repr__(self):
        return repr(self.__handle__.value)

    def __float__(self):
        return float(self.__handle__.value)

    def __str__(self):
        return str(self.__handle__.value)

    def __int__(self):
        return self.__handle__.value

    def __bool__(self):
        return self.__handle__.value != 0


class UShort(int, metaclass=_Ct):
    base = "unsigned short"

    def __new__(cls, value, *args, **kwargs):
        _tp_check((value,), int)
        if value < 0:
            raise ValueError("Unsigned integer values cannot be negative.")
        size = int(value.bit_length() / 8)
        if size > cls.__size__:
            raise MemoryError(f"Too big integer value: expected {cls.__size__} bytes max, but got {size}.")
        return cls.create_instance(value, *args, **kwargs)

    def __repr__(self):
        return repr(self.__handle__.value)

    def __float__(self):
        return float(self.__handle__.value)

    def __str__(self):
        return str(self.__handle__.value)

    def __int__(self):
        return self.__handle__.value

    def __bool__(self):
        return self.__handle__.value != 0


class Long(int, metaclass=_Ct):
    base = "long"

    def __new__(cls, value, *args, **kwargs):
        _tp_check((value,), int)
        size = int(value.bit_length() / 8)
        if size > cls.__size__:
            raise MemoryError(f"Too big integer value: expected {cls.__size__} bytes max, but got {size}.")
        return cls.create_instance(value, *args, **kwargs)

    def __repr__(self):
        return repr(self.__handle__.value)

    def __float__(self):
        return float(self.__handle__.value)

    def __str__(self):
        return str(self.__handle__.value)

    def __int__(self):
        return self.__handle__.value

    def __bool__(self):
        return self.__handle__.value != 0


class ULong(int, metaclass=_Ct):
    base = "unsigned long"

    def __new__(cls, value, *args, **kwargs):
        _tp_check((value,), int)
        if value < 0:
            raise ValueError("Unsigned integer values cannot be negative.")
        size = int(value.bit_length() / 8)
        if size > cls.__size__:
            raise MemoryError(f"Too big integer value: expected {cls.__size__} bytes max, but got {size}.")
        return cls.create_instance(value, *args, **kwargs)

    def __repr__(self):
        return repr(self.__handle__.value)

    def __float__(self):
        return float(self.__handle__.value)

    def __str__(self):
        return str(self.__handle__.value)

    def __int__(self):
        return self.__handle__.value

    def __bool__(self):
        return self.__handle__.value != 0


class Int(int, metaclass=_Ct):
    base = "int"

    def __new__(cls, value, *args, **kwargs):
        _tp_check((value,), int)
        size = int(value.bit_length() / 8)
        if size > cls.__size__:
            raise MemoryError(f"Too big integer value: expected {cls.__size__} bytes max, but got {size}.")
        return cls.create_instance(value, *args, **kwargs)

    def __repr__(self):
        return repr(self.__handle__.value)

    def __float__(self):
        return float(self.__handle__.value)

    def __str__(self):
        return str(self.__handle__.value)

    def __int__(self):
        return self.__handle__.value

    def __bool__(self):
        return self.__handle__.value != 0


class UInt(int, metaclass=_Ct):
    base = "unsigned int"

    def __new__(cls, value, *args, **kwargs):
        _tp_check((value,), int)
        if value < 0:
            raise ValueError("Unsigned integer values cannot be negative.")
        size = int(value.bit_length() / 8)
        if size > cls.__size__:
            raise MemoryError(f"Too big integer value: expected {cls.__size__} bytes max, but got {size}.")
        return cls.create_instance(value, *args, **kwargs)

    def __repr__(self):
        return repr(self.__handle__.value)

    def __float__(self):
        return float(self.__handle__.value)

    def __str__(self):
        return str(self.__handle__.value)

    def __int__(self):
        return self.__handle__.value

    def __bool__(self):
        return self.__handle__.value != 0


class LongLong(int, metaclass=_Ct):
    base = "long long"

    def __new__(cls, value, *args, **kwargs):
        _tp_check((value,), int)
        size = int(value.bit_length() / 8)
        if size > cls.__size__:
            raise MemoryError(f"Too big integer value: expected {cls.__size__} bytes max, but got {size}.")
        return cls.create_instance(value, *args, **kwargs)

    def __repr__(self):
        return repr(self.__handle__.value)

    def __float__(self):
        return float(self.__handle__.value)

    def __str__(self):
        return str(self.__handle__.value)

    def __int__(self):
        return self.__handle__.value

    def __bool__(self):
        return self.__handle__.value != 0


class ULongLong(int, metaclass=_Ct):
    base = "unsigned long long"

    def __new__(cls, value, *args, **kwargs):
        _tp_check((value,), int)
        if value < 0:
            raise ValueError("Unsigned integer values cannot be negative.")
        size = int(value.bit_length() / 8)
        if size > cls.__size__:
            raise MemoryError(f"Too big integer value: expected {cls.__size__} bytes max, but got {size}.")
        return cls.create_instance(value, *args, **kwargs)

    def __repr__(self):
        return repr(self.__handle__.value)

    def __float__(self):
        return float(self.__handle__.value)

    def __str__(self):
        return str(self.__handle__.value)

    def __int__(self):
        return self.__handle__.value

    def __bool__(self):
        return self.__handle__.value != 0

