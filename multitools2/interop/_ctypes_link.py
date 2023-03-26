import ctypes

from ._characters import Char, WChar
from ._integers import Short, UShort, Int, UInt, Long, ULong, LongLong, ULongLong
from .._internal import *


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


class AccessViolationType:
    __read__ = None
    __write__ = None
    __none__ = None

    def __init__(self, x):
        self.type = x

    def __repr__(self):
        return f"<AccessViolationType.{self.type}>"

    def __bool__(self):
        return self.type != 'none'

    @classmethod
    @property
    def read(cls):
        """
        Read / Write access violation.
        If you can't read, you can't write. Reverse is not true.
        """
        if cls.__read__ is None:
            cls.__read__ = cls('read')
        return cls.__read__

    @classmethod
    @property
    def write(cls):
        """
        Write access violation.
        """
        if cls.__write__ is None:
            cls.__write__ = cls('write')
        return cls.__write__

    @classmethod
    @property
    def none(cls):
        """
        No access violation.
        """
        if cls.__none__ is None:
            cls.__none__ = cls('none')
        return cls.__none__


@scope_at(__NAME__, 'interop')
class AccessViolationError(MemoryError):  # should we inherit MemoryError or OSError?
    """
    Memory access violation.
    This usually happens when the current thread tries to access memory it is not
    allowed to.
    """
    def __init__(self, address, av_type):
        formatted = av_type.type + ' at 0x' + hex(address).removeprefix('0x').zfill(16).upper()
        super().__init__(formatted)

        self.address = address
        """The invalid address the user tried to access."""
        self.formatted = formatted
        """A formatted version of the address."""
        self.type = av_type
        """AccessViolationType object."""


def validate_address(address):
    """
    Return whether the given memory address can be read or written.
    """
    if address < (256 ** 4):   # addresses of 4 bytes or fewer are usually not readable
        return AccessViolationType.read

    to_test = ctypes.cast(ctypes.c_void_p(address), ctypes.POINTER(ctypes.c_char))  # address to test is converted to char*
    temp = ctypes.create_string_buffer(0, 1)  # temporary copy buffer

    try:
        # we use memcpy to trigger an eventual access violation
        ctypes.cdll.msvcrt.memcpy(temp, to_test, 1)
    except OSError as e:
        msg = e.args
        if (len(msg) > 0) and isinstance(msg[0], str):
            if msg[0].startswith('exception: access violation reading'):
                return AccessViolationType.read  # you can write only if you can read. Reverse is not true.
        raise

    try:
        # use memcpy the other way to trigger eventual writing access violation: we need to test for readonly memory
        ctypes.cdll.msvcrt.memcpy(to_test, temp, 1)
    except OSError as e:
        msg = e.args
        if (len(msg) > 0) and isinstance(msg[0], str):
            if msg[0].startswith('exception: access violation writing'):
                return AccessViolationType.write

        raise

    return AccessViolationType.none

