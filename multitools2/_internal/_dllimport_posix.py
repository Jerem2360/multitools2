import _ctypes
import sys


"""
Non-Windows stuff
"""


from ._dllimport import *


class _Posix_Resource(Resource):
    """
    Represent a posix-specific resource.
    """
    def __new__(cls, value):
        if isinstance(value, int):
            self = super().__new__(cls, value)
            self._data = None
            return self
        if isinstance(value, str):
            data = ctypes.c_char_p(bytes(value, encoding=sys.getdefaultencoding()))
        elif isinstance(value, bytes):
            data = ctypes.c_char_p(value)
        if isinstance(value, (str, bytes)):
            # noinspection PyUnboundLocalVariable
            self = super().__new__(cls, ctypes.addressof(data))
            # noinspection PyUnboundLocalVariable
            self._data = data
            return self

    def as_char_p(self):
        ctypes.cast(int(self), RESOURCE)


class DllHandle(DynamicResource):
    def __new__(cls, value):
        return super().__new__(cls, value)

    def release(self):
        _ctypes.dlclose(int(self))

    @staticmethod
    def open(name, flags):
        return DllHandle(_ctypes.dlopen(name, flags))

    def symbol(self, sym: Resource):
        return DynamicResource(_ctypes.dlsym(int(self), sym))


def make_resource(name_or_ordinal) -> Resource | None:
    if isinstance(name_or_ordinal, (int, str, bytes)):
        return _Posix_Resource(name_or_ordinal)
    return None

