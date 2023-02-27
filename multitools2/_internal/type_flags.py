"""
Internal utililty allowing to access a type's flags from
python code.

Note:
    Allowing modification of these flags could easily cause the
    interpreter to fail or crash, so we prefer not to.
"""

import ctypes
import sys

from . import ctypes_defs


TPFLAGS_HEAPTYPE = 1 << 9
TPFLAGS_IS_ABSTRACT = 1 << 20


def flags(cls):
    # to do use type.__flags__ instead
    if not isinstance(cls, type):
        return 0
    cls_p = ctypes.cast(id(cls), ctypes_defs._typeobject_p)
    cls_struct = cls_p.contents
    flags = cls_struct.tp_flags
    return flags

