from dataclasses import dataclass

from .. import _misc
from ._field import FieldWrapper


@dataclass
class ClsData(metaclass=_misc.SimpleMeta):
    """
    Internal data structure for storing info about multitools classes
    """
    name: str
    abstract: bool
    field_defs: tuple[str]
    static_fields: dict[str, FieldWrapper]
    instance_fields: dict[str, FieldWrapper]
    bases: tuple[type]
    abs_locked: bool
    mro: tuple[type]

