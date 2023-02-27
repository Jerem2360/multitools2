import ctypes

from ._characters import Char, WChar
from ._integers import Short, UShort, Int, UInt, Long, ULong, LongLong, ULongLong


my_to_ctypes = {
    Char: ctypes.c_char,
    WChar: ctypes.c_wchar,
    Short: ctypes.c_short,
    UShort: ctypes.c_ushort,
    Int: ctypes.c_int,
    UInt: ctypes.c_uint,
    Long: ctypes.c_long,
    ULong: ctypes.c_ulong,
    LongLong: ctypes.c_longlong,
    ULongLong: ctypes.c_ulonglong,
}


ctypes_to_my = {}

for k, v in my_to_ctypes.items():
    ctypes_to_my[v] = k

