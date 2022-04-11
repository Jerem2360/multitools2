from ._base import CType as _Ct
from .._r import type_check as _tp_check


class Bool(int, metaclass=_Ct):
    base = "bool"

    def __new__(cls, value, *args, **kwargs):
        if value == 0:
            value = False
        _tp_check((value,), bool)
        return super().__new__(cls, int(value))

    def __repr__(self):
        return repr(bool(self)).lower()

