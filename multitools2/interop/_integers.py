import sys

from .._internal import errors
from .._internal import type_check
from ._basis import *


def _check_int_size(value, max_bytes, signed):
    high_limit = 256 ** max_bytes
    if signed:
        high_limit //= 2
    low_limit = 0
    if signed:
        low_limit = -high_limit
    return low_limit <= value < high_limit


class Short(ForeignData, struct_type='h'):
    def __init__(self, value: int | SupportsIndex):
        type_check.parse(int | SupportsIndex, value)
        if not _check_int_size(value, self.__size__, True):
            raise OverflowError("Integer too large.") from errors.configure(depth=1)
        super().__init__(value.__index__())


class UShort(ForeignData, struct_type='H'):
    def __init__(self, value: int | SupportsIndex):
        type_check.parse(int | SupportsIndex, value)
        if not _check_int_size(value, self.__size__, False):
            raise OverflowError("Integer too large.") from errors.configure(depth=1)
        super().__init__(value.__index__())


class Int(ForeignData, struct_type='i'):
    def __init__(self, value: int | SupportsIndex):
        type_check.parse(int | SupportsIndex, value)
        if not _check_int_size(value, self.__size__, True):
            raise OverflowError("Integer too large.") from errors.configure(depth=1)
        super().__init__(value.__index__())


class UInt(ForeignData, struct_type='I'):
    def __init__(self, value: int | SupportsIndex):
        type_check.parse(int | SupportsIndex, value)
        if not _check_int_size(value, self.__size__, False):
            raise OverflowError("Integer too large.") from errors.configure(depth=1)
        super().__init__(value.__index__())


class Long(ForeignData, struct_type='l'):
    def __init__(self, value: int | SupportsIndex):
        type_check.parse(int | SupportsIndex, value)
        if not _check_int_size(value, self.__size__, True):
            raise OverflowError("Integer too large.") from errors.configure(depth=1)
        super().__init__(value.__index__())


class ULong(ForeignData, struct_type='L'):
    def __init__(self, value: int | SupportsIndex):
        type_check.parse(int | SupportsIndex, value)
        if not _check_int_size(value, self.__size__, False):
            raise OverflowError("Integer too large.") from errors.configure(depth=1)
        super().__init__(value.__index__())


class LongLong(ForeignData, struct_type='q'):
    def __init__(self, value: int | SupportsIndex):
        type_check.parse(int | SupportsIndex, value)
        if not _check_int_size(value, self.__size__, True):
            raise OverflowError("Integer too large.") from errors.configure(depth=1)
        super().__init__(value.__index__())


class ULongLong(ForeignData, struct_type='Q'):
    def __init__(self, value: int | SupportsIndex):
        type_check.parse(int | SupportsIndex, value)
        if not _check_int_size(value, self.__size__, False):
            raise OverflowError("Integer too large.") from errors.configure(depth=1)
        super().__init__(value.__index__())


class Py_ssize_t(ForeignData, struct_type='q'):
    def __init__(self, value: int | SupportsIndex):
        type_check.parse(int | SupportsIndex, value)
        if not _check_int_size(value, self.__size__, True):
            raise OverflowError("Integer too large.") from errors.configure(depth=1)
        super().__init__(value.__index__())


class Size_t(ForeignData, struct_type='Q'):
    def __init__(self, value: int | SupportsIndex):
        type_check.parse(int | SupportsIndex, value)
        if not _check_int_size(value, self.__size__, False):
            raise OverflowError("Integer too large.") from errors.configure(depth=1)
        super().__init__(value.__index__())


