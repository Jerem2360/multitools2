from ._base import CType as _Ct


class Short(int, metaclass=_Ct):
    base = 'short'


class UShort(int, metaclass=_Ct):
    base = 'ushort'

    def __new__(cls, value, *args, **kwargs):
        self = super().__new__(cls, value)
        if self < 0:
            raise ValueError("Unsigned integer values cannot be negative.")
        return self


class Long(int, metaclass=_Ct):
    base = 'long'


class ULong(int, metaclass=_Ct):
    base = 'ulong'

    def __new__(cls, value, *args, **kwargs):
        self = super().__new__(cls, value)
        if self < 0:
            raise ValueError("Unsigned integer values cannot be negative.")
        return self


class Int(int, metaclass=_Ct):
    base = 'int'


class UInt(int, metaclass=_Ct):
    base = 'uint'

    def __new__(cls, value, *args, **kwargs):
        self = super().__new__(cls, value)
        if self < 0:
            raise ValueError("Unsigned integer values cannot be negative.")
        return self


class LongLong(float, metaclass=_Ct):
    base = "long long"


class ULongLong(float, metaclass=_Ct):
    base = "ulong long"

    def __new__(cls, value, *args, **kwargs):
        self = super().__new__(cls, value)
        if self < 0:
            raise ValueError("Unsigned integer values cannot be negative.")
        return self

