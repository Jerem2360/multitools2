from ..errors import *
from dataclasses import dataclass
from typing import Any as _Any


@dataclass
class Address:
    address: str
    port: int


@dataclass
class User:
    address: Address
    sock: _Any


class Package:
    def __init__(self, data):
        """
        Packages containing raw bytes that can be sent through a 'net.Socket' socket.
        Has various methods for converting to and from 'int', 'float', 'bool' and 'str'.
        """
        if not isinstance(data, bytes):
            raise SimpleTypeError(type(data), bytes)

        self.__data = data

    def __str__(self):
        """
        Implement str(self)
        """
        return str(self.__data)

    def __repr__(self):
        """
        Implement repr(self)
        """
        return f"<Package at 0x{str(hex(id(self))).removeprefix('0x').upper()}, " \
               f"data={repr(self.__data)}>"

    def __len__(self):
        """
        Implement len(self) as returning the length of
        the bytes the Package contains.
        """
        return len(self.__data)

    def to_int(self, byteorder='big'):
        """
        Convert self to a plain integer, with byte order 'byteorder'
        defaulting to "big".
        """
        return int.from_bytes(self.__data, byteorder)

    def to_str(self, encoding='Utf-8'):
        """
        Convert self to a string, with encoding 'encoding'
        defaulting to "utf-8".
        """
        return str(self.__data, encoding=encoding)

    def to_bool(self, byteorder='big'):
        """
        Convert self to a plain boolean, with byte order 'byteorder'
        defaulting to "big".
        """
        return bool.from_bytes(self.__data, byteorder)

    def to_float(self, byteorder='big'):
        """
        Convert self to a floating point, with byte order 'byteorder'
        defaulting to "big".
        """
        threshold_b = self.__data[:3]
        num_b = self.__data[4:7]
        threshold = int.from_bytes(threshold_b, byteorder)
        num = int.from_bytes(num_b, byteorder)
        float_result = num / threshold
        return float_result

    @staticmethod
    def from_int(value, byteorder='big'):
        """
        Create and return a new Package from an integer of bit length <= 4.
        """
        value_b = value.to_bytes(4, byteorder)
        return Package(value_b)

    @staticmethod
    def from_long(value, byteorder='big'):
        """
        Create and return a new Package from an integer of bit length <= 8.
        """
        value_b = value.to_bytes(8, byteorder)
        return Package(value_b)

    @staticmethod
    def from_str(value, encoding='Utf-8'):
        """
        Create an return a new Package from a string object encoded in 'encoding'.
        """
        value_b = bytes(value, encoding=encoding)
        return Package(value_b)

    @staticmethod
    def from_bool(value, byteorder='big'):
        """
        Create and return a new Package from a boolean.
        """
        value_b = value.to_bytes(1, byteorder)
        return Package(value_b)

    @staticmethod
    def from_float(value: float, byteorder='big'):
        """
        Create and return a new Package from a floating point of bit length <= 8.
        """
        parts = str(value).split('.')
        n_decimals = len(parts[1])
        if parts[1] == str(0):
            n_decimals = 0

        threshold = 10 ** n_decimals
        integer_float = int(value * threshold)
        value_b = threshold.to_bytes(4, byteorder) + integer_float.to_bytes(4, byteorder)
        return Package(value_b)

    @staticmethod
    def from_double(value: float, byteorder='big'):
        """
        Create and return a new Package from a floating point of bit length <= 16.
        """
        parts = str(value).split('.')
        n_decimals = len(parts[1])
        if parts[1] == str(0):
            n_decimals = 0

        threshold = 10 ** n_decimals
        integer_float = int(value * threshold)
        value_b = threshold.to_bytes(8, byteorder) + integer_float.to_bytes(8, byteorder)
        return Package(value_b)

    data = property(lambda self: self.__data)  # The actual bytes that are stored into the Package.

