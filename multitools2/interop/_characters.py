import sys

from ._basis import *
from .._internal import type_check


class Char(ForeignData, struct_type='c'):
    def __init__(self, value: str):
        type_check.parse(str, value)
        if len(value) != 1:
            raise ValueError("A single character is required.") from errors.configure(depth=1)
        value_b = bytes(value, encoding=sys.getdefaultencoding())
        super().__init__(value_b)

    @classmethod
    def __ptr_as_obj__(cls, address) -> object:
        """
        Convert Pointer[Char] and Array[Char] to a str instance
        """
        result = ""

        while True:
            char = address.deref()
            if not char.id:
                break
            result += char.as_object()


        return result

    def as_object(self) -> tuple[object] | object:
        value_b = self.__unpack__(self.__memory__.view())[0]
        return str(value_b, encoding=sys.getdefaultencoding())

    @property
    def id(self):
        return int.from_bytes(bytes(self.__memory__), sys.byteorder, signed=False)


class WChar(ForeignData, struct_type='h'):
    # using short here as struct does not support unicode
    def __init__(self, value):
        type_check.parse(str, value)
        if len(value) != 1:
            raise ValueError("A single character is required.") from errors.configure(depth=1)
        super().__init__(ord(value))

    def as_object(self) -> tuple[object] | object:
        ordinal = super().as_object()
        return chr(ordinal)

    @property
    def id(self) -> int:
        return super().as_object()

