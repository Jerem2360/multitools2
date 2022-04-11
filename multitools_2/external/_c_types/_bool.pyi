from ._base import CType as _CType


class Bool(int, metaclass=_CType):
    def __new__(cls, value: bool, *args, **kwargs) -> Bool: ...
    def __repr__(self) -> str: ...

