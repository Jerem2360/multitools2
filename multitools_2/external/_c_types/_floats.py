from ._base import CType as _Ct


class Float(float, metaclass=_Ct):
    base = "float"


class Double(float, metaclass=_Ct):
    base = "double"


class LongDouble(float, metaclass=_Ct):
    base = "long double"



