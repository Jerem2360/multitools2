
__all__ = [
    "config",
    "ForeignData",
    "void",
    "Pointer",
    "Array",

    "Short",
    "UShort",
    "Int",
    "UInt",
    "Long",
    "ULong",
    "LongLong",
    "ULongLong",
]

import warnings

_ver = {
    "C++": [98, 11, 14, 17, 20],
    "C": [89, 99, 11],
}
_default = {
    "C++": 14,
    "C": 11,
}


from dataclasses import dataclass
from typing import Literal, overload

_CVersion = Literal[10, 11]


@dataclass
class _Config:
    version: Literal[89, 98, 99, 11, 14, 17, 20] = 11
    name: Literal["C", "C++"] = "C"
    hosted: bool = False

    @overload
    def set(self, *,
            name: Literal["C"] = ...,
            version: Literal[89, 99, 11] = ...,
            hosted: bool = ...
            ) -> None: ...

    @overload
    def set(self, *,
            name: Literal["C++"] = ...,
            version: Literal[98, 11, 14, 17, 20] = ...,
            hosted: bool = ...,
            ) -> None: ...

    def set(self, **kwargs):
        name = kwargs.get('name', self.name)
        if name not in _ver:
            raise ValueError(f"Unknown standard type \"{name}\".")

        version = kwargs.get('version', self.version)
        if version not in _ver[name]:
            warnings.warn(
                UserWarning(f"Unknown version '{version}' for standard type \"{name}\". Using default version '{_default[name]}'."),
                stacklevel=2
            )
            version = _default[name]
        hosted = kwargs.get('hosted', self.hosted)

        self.name = name
        self.version = version
        self.hosted = hosted

    def __repr__(self):
        return f"<extern \"{self.name}\" {self.version}>"


config = _Config()


from ._base import ForeignData, void
from ._pointer import Pointer
from ._array import Array
from ._integers import Short, UShort, Int, UInt, Long, ULong, LongLong, ULongLong

