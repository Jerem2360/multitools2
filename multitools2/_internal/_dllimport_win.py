import ctypes
import sys

import _ctypes

"""
Windows-specific stuff
"""


_GetProcAddress = ctypes.windll.kernel32.GetProcAddress
_GetProcAddress.argtypes = ctypes.c_void_p, ctypes.c_char_p
_GetProcAddress.restype = ctypes.c_void_p


from ._dllimport import *


def _err_from_windows_error(code):
    return OSError(None, ctypes.FormatError(code), None, code)


def _MAKE_INTRESOURCE(num):
    """
    char* 'Windows.h':: MAKEINTRESOURCE(unsigned __int64 source)
    Convert an integer ordinal to a char* representing an integer resource
    """
    bytes_ = num.to_bytes(8, sys.byteorder)[:2]
    res = int.from_bytes(bytes_, sys.byteorder)
    return res  # -> (char*)MAKE_INTRESOURCE(num)


class _Win_IntResource(Resource):
    def __new__(cls, value):
        resource = value if cls.check(value) else _MAKE_INTRESOURCE(value)
        return super().__new__(cls, resource)

    @staticmethod
    def check(value):
        """
        int 'Windows.h':: IS_INTRESOURCE(char* data)
        """
        return (value >> 16) == 0

    def as_char_p(self):
        """
        Return the integer resource as a char*
        """
        return ctypes.cast(int(self), RESOURCE)


class _Win_StringResource(Resource):
    def __new__(cls, value):
        if isinstance(value, str):
            value = bytes(value, encoding=sys.getdefaultencoding())
        data = ctypes.c_char_p(value)
        self = super().__new__(cls, ctypes.addressof(data))
        self._data = data
        return self

    def as_char_p(self):
        return self._data

    @property
    def contents(self):
        return str(self._data.value, encoding=sys.getdefaultencoding())


class DllHandle(DynamicResource):
    """
    A reference to a library that has been loaded into memory.
    Supported library types are:

    -> Windows:
        .exe
        .dll
        .sys
        other files using the PE library format
    -> Other OS:
        .so
        executables

    Note: Some supported file types may or may not figure in this list, depending
    on your platform. For more information, refer to your operating system's documentation *
    for dynamic libraries.
    """
    def __new__(cls, value):
        return super().__new__(cls, value)

    def release(self):
        _ctypes.FreeLibrary(int(self))

    @staticmethod
    def open(name, flags):
        return DllHandle(_ctypes.LoadLibrary(name, flags))

    def symbol(self, sym: Resource):
        res = _GetProcAddress(self.as_void_p(), sym.as_char_p())
        if res in (0, None):
            raise _err_from_windows_error(ctypes.GetLastError())
        return DynamicResource(res)


def make_resource(name_or_ordinal) -> Resource | None:
    if isinstance(name_or_ordinal, int):
        return _Win_IntResource(name_or_ordinal)
    if isinstance(name_or_ordinal, str):
        return _Win_StringResource(name_or_ordinal)
    return None

