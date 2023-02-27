from ._basis import ForeignData, Pointer, void
from ._integers import Short, UShort, Int, UInt, Long, ULong, LongLong, ULongLong, Size_t, Py_ssize_t
from ._characters import Char, WChar
from ._struct import Structure


__all__ = [
    'ForeignData',
    'Pointer',
    'void',
    'Structure',

    # integer types:
    'Short',
    'UShort',
    'Int',
    'UInt',
    'Long',
    'ULong',
    'LongLong',
    'ULongLong',
    'Size_t',
    'Py_ssize_t',

    # character types:
    'Char',
    'WChar'
]


"""x = Int(140)
xp = Pointer[Int](x)

print(x.__memory__.address, xp.as_object())"""

