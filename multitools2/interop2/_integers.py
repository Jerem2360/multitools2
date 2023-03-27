from ._base import *
from ._pointer import *
from .._internal.errors import *
from .._internal import errors, type_check

import struct


def _check_int_size(integer, maxsize, signed=True):
    if signed:
        if not (-(256 ** maxsize) / 2 < integer < (256 ** maxsize) / 2 - 1):
            raise TypeError(f"Integer too large to fit in {maxsize} bytes.") from configure(depth=2)
    else:
        if not (-1 < integer < (256 ** maxsize) - 1):
            raise TypeError(f"Integer too large to fit in {maxsize} bytes.") from configure(depth=2)


class Short(ForeignData, type='h'):
    def __init__(self, value):
        type_check.parse(SupportsIndex, value)
        _check_int_size(value.__index__(), self.__size__)
        super().__init__(value.__index__())


class UShort(ForeignData, type='H'):
    def __init__(self, value):
        type_check.parse(SupportsIndex, value)
        _check_int_size(value.__index__(), self.__size__, signed=False)
        super().__init__(value.__index__())


class Int(ForeignData, type='i'):
    def __init__(self, value):
        type_check.parse(SupportsIndex, value)
        _check_int_size(value.__index__(), self.__size__)
        super().__init__(value.__index__())


class UInt(ForeignData, type='I'):
    def __init__(self, value):
        type_check.parse(SupportsIndex, value)
        _check_int_size(value.__index__(), self.__size__, signed=False)
        super().__init__(value.__index__())


class Long(ForeignData, type='l'):
    def __init__(self, value):
        type_check.parse(SupportsIndex, value)
        _check_int_size(value.__index__(), self.__size__)
        super().__init__(value.__index__())


class ULong(ForeignData, type='L'):
    def __init__(self, value):
        type_check.parse(SupportsIndex, value)
        _check_int_size(value.__index__(), self.__size__, signed=False)
        super().__init__(value.__index__())


class LongLong(ForeignData, type='q'):
    def __init__(self, value):
        type_check.parse(SupportsIndex, value)
        _check_int_size(value.__index__(), self.__size__)
        super().__init__(value.__index__())


class ULongLong(ForeignData, type='Q'):
    def __init__(self, value):
        type_check.parse(SupportsIndex, value)
        _check_int_size(value.__index__(), self.__size__, signed=False)
        super().__init__(value.__index__())


class SSize_t(ForeignData, type='n'):
    def __init__(self, value):
        type_check.parse(SupportsIndex, value)
        _check_int_size(value.__index__(), self.__size__)
        super().__init__(value.__index__())


class Size_t(ForeignData, type='N'):
    def __init__(self, value):
        type_check.parse(SupportsIndex, value)
        _check_int_size(value.__index__(), self.__size__, signed=False)
        super().__init__(value.__index__())

