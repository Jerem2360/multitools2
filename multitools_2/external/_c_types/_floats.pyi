from ._base import CType as _CType


class Float(float, metaclass=_CType): pass
class Double(float, metaclass=_CType): pass
class LongDouble(float, metaclass=_CType): pass

