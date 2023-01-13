import ctypes

from .. import *
from ..interop import *


if _MS_WIN32:
    class _mmap_object(Struct):
        ob_base: PyObject
        data: Pointer[Char]
        size: SSize_t
        pos: SSize_t
        offset: LongLong
        exports: SSize_t
        handle: ULongLong
        file_handle: ULongLong
        tag_name: Pointer[Char]

else:
    class _mmap_object(Struct):
        ob_base: PyObject
        data: Pointer[Char]
        size: SSize_t
        pos: SSize_t
        offset: Long
        exports: SSize_t
        fd: Int


@dllimport("kernel32", callconv=__stdcall)
def CreateFileMapping()

