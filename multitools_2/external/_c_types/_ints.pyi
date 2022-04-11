from ._base import CType as _CType


class Short(int, metaclass=_CType): pass
class UShort(int, metaclass=_CType): pass
class Long(int, metaclass=_CType): pass
class ULong(int, metaclass=_CType): pass
class Int(int, metaclass=_CType): pass
class UInt(int, metaclass=_CType): pass
class LongLong(int, metaclass=_CType): pass
class ULongLong(int, metaclass=_CType): pass

