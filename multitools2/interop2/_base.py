import struct
from typing import overload

import _ctypes

from .._internal.meta import *
from .._internal import *
from .._internal import type_check
from .._internal.interface import *
from .._internal.errors import *
from .._internal import memory


_INTEROP_NAME = __NAME__ + '.interop2'


@scope_at(_INTEROP_NAME)
@abstract
class ForeignData(metaclass=MultiMeta):
    """
    Base class for all external data types.
    """

    __slots__ = [
        '__memory__'
    ]

    __size__ = 0
    __type__ = ''

    def __new__(cls, *args, **kwargs):
        """
        Create and return new external data.
        """
        size = kwargs.get('size', cls.__size__)
        type_check.parse(SupportsIndex, size)
        cls.__size__ = size.__index__()

        if not cls.__size__:
            raise TypeError(f"Foreign data type '{cls.__name__}' cannot be instantiated.") from configure(depth=1)

        self = object.__new__(cls)
        self.__memory__ = memory.Memory(size)
        return self

    def __init__(self, *data):
        """
        Initialize a foreign variable, given arguments.
        This gets called each time the instances value is set
        by python code.
        """
        self.__pack__(*data, buffer=self.__memory__.view())

    def __init_subclass__(cls, **kwargs):
        """
        Initialize a foreign data type.
        """
        size = kwargs.get('size', None)
        type_ = kwargs.get('type', None)

        if getattr(cls, '__size__', 0) and getattr(cls, '__type__', ''):
            return

        if (size is None) and (type_ is not None):
            try:
                size = struct.calcsize(type_)
            except struct.error:
                raise TypeError("Bad type string format.") from configure(depth=1)
        elif (size is not None) and (type_ is None):
            type_ = '.'
        else:
            raise ValueError("Foreign data types must at least specify a type string or a size.") from configure(depth=1)

        cls.__size__ = size
        cls.__type__ = type_

    def __repr__(self):
        from . import config
        return f"<{config.name} ({type(self).__name__}){self.as_object()}>"

    @overload
    @classmethod
    def __pack__(cls, *data) -> bytes: ...
    @overload
    @classmethod
    def __pack__(cls, *data, buffer: Buffer) -> None: ...

    @classmethod
    def __pack__(cls, *data, buffer=None):
        type_check.parse(Buffer | None, buffer)
        if buffer is not None:
            return struct.pack_into(cls.__type__, buffer, 0, *data)
        return struct.pack(cls.__type__, *data)

    @classmethod
    def __unpack__(cls, buffer: Buffer | memory.Memory):
        type_check.parse(SupportsBytes, buffer)
        res = struct.unpack(cls.__type__, bytes(buffer))
        if len(res) == 1:
            return res[0]
        return res

    @classmethod
    def __pointer_as_object__(cls, pointer, address) -> object:
        """
        Convert a pointer to this type to a python object.
        Return value of None means NULL.
        Default behaviour uses the object's address.
        """
        return NotImplemented

    @classmethod
    def __pointer_from_object__(cls, obj) -> int:
        """
        Convert a python object to a pointer to this type.
        An integer address must be returned.
        """
        return NotImplemented

    def update(self, buffer):
        """
        Update the object's memory from a given buffer.
        Data is copied.
        """
        type_check.parse(SupportsBytes, buffer)
        if len(buffer) != type(self).__size__:
            raise ValueError("Memory must be updated with data of the same length.") from configure(depth=1)
        self.__memory__[:] = bytes(buffer)

    def set(self, *args):
        """
        Set the value of self.
        args must match the same pattern as for __init__.
        """
        with errors.frame_mask:
            self.__init__(*args)

    def as_object(self) -> object:
        """
        Convert self to a python object.
        """
        return self.__unpack__(self.__memory__)

    @classmethod
    def from_memory(cls, mem):
        """
        Initialize a new instance from already allocated memory.
        BufferUnderflowError is raised if the buffer is too small.
        """
        type_check.parse(memory.Memory, mem)
        self = cls.__new__(cls)
        if len(mem) > cls.__size__:
            self.__memory__ = mem.get_segment(range(cls.__size__))
        elif len(mem) == cls.__size__:
            self.__memory__ = mem
        else:
            raise BufferUnderflowError(f"Not enough space to store an instance of '{cls.__name__}'.") from configure(depth=1)
        return self


@scope_at(_INTEROP_NAME)
@final
class void(ForeignData, size=0):
    """
    The 'void' type. It is only allowed as a template
    argument to the Pointer class.
    """
    @classmethod
    def __pack__(cls, *data, buffer=None):
        type_check.parse(Buffer | None, buffer)
        if buffer is None:
            return b''

    @classmethod
    def __unpack__(cls, buffer):
        type_check.parse(SupportsBytes, buffer)

    @classmethod
    def __pointer_as_object__(cls, pointer):
        return super(type(pointer), pointer).as_object()

    @classmethod
    def __pointer_from_object__(cls, obj):
        type_check.parse(SupportsIndex, obj)
        return obj

    @classmethod
    def from_memory(cls, mem):
        raise TypeError("Foreign data type 'void' cannot be instantiated.") from configure(depth=1)


@scope_at(__NAME__)
class BufferOverflowError(BufferError): ...


@scope_at(__NAME__)
class BufferUnderflowError(BufferError): ...
