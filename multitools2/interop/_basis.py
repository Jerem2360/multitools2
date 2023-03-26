import struct
import sys
import weakref

from .._internal import *
from .._internal.meta import *
from .._internal import memory
from .._internal import errors
from .._internal.interface import *
from .._internal import type_check
from .._internal._typeshed import *


byteorders = {
    'little': '<',
    'big': '>',
}


class ForeignData_Meta(MultiMeta):
    def __new__(mcs, name, bases, np, **kwargs):
        with errors.frame_mask:
            cls = MultiMeta.__new__(mcs, name, bases, np, **kwargs)
        return cls


@abstract
class ForeignData(metaclass=ForeignData_Meta):
    """
    Base class for all foreign data types.

    Calling 'ForeignData(*initializer)' results in a foreign instance
    whose contents are initialized given initializer.

    For fundamental types, initializers are simply the corresponding
    literals. For types composed of multiple members such as structures
    or arrays, initializers are tuples or lists giving individual values
    for each of the elements. For the constructors, these can be
    passed in as multiple arguments.
    Pointer initializers are the actual object the pointer must point to:

    In C, you would write:
    T* t_p = &p

    With this python library, you would write:
    t_p = Pointer[T](t)

    Note that foreign variables are all mutable.
    """

    __size__ = 0
    __struct_type__ = '.'

    def __new__(cls, *args, size=None, **kwargs):
        """
        Allocate memory for a new foreign variable.
        """
        if size is None:
            size = cls.__size__
        type_check.parse(int | SupportsIndex, size)
        size = size.__index__()

        if not size:
            raise TypeError(f"Raw foreign data types must specify a size.") from errors.configure(depth=1)

        self = object.__new__(cls)
        self.__memory__ = memory.Memory(size)
        return self

    def __init__(self, *data):
        """
        Initialize a foreign variable's value, given the packing arguments.
        """
        self.__pack__(*data, _mem=self.__memory__.view())


    def __init_subclass__(cls, **kwargs):
        """
        Implement subclassing.
        At least one of these parameters are required:
        'size': The size of this type in bytes.
        'struct_type': The struct format for this type. See the struct module for more info.
        """
        cls.__size__ = kwargs.get('size', 0)
        cls.__struct_type__ = kwargs.get('struct_type', '.')

        if not cls.__size__:
            try:
                cls.__size__ = struct.calcsize(cls.__struct_type__)
            except struct.error:
                if cls.__struct_type__ == '.':
                    raise TypeError("Either 'size' or 'struct_type' must be specified for a foreign data type.") from errors.configure(depth=1)
                raise TypeError(f"Invalid struct format '{cls.__struct_type__}'") from errors.configure(depth=1)

    def __repr__(self):
        return f"<extern \"C\" ({type(self).__name__}){repr(self.as_object())}>"

    @classmethod
    def __pack__(cls, *data, _mem=None):
        """
        Implement data packing.
        This converts the arguments into usable bytes. If _mem
        is provided, the bytes are directly packed into it.
        """
        if _mem is None:
            return struct.pack(cls.__struct_type__, *data)
        try:
            struct.pack_into(cls.__struct_type__, _mem, 0, *data)
        except struct.error as e:
            raise ValueError(*e.args) from errors.configure(depth=1)

    @classmethod
    def __unpack__(cls, buffer):
        """
        Implement data unpacking.
        This converts bytes into human-readable value(s).
        """
        buffer = bytes(buffer)
        return struct.unpack(cls.__struct_type__, buffer)

    def as_object(self) -> tuple[object] | object:
        """
        Convert the current foreign instance into a python object.
        This may not be implemented for special data types, in which
        case the default structure behaviour is used instead.
        """
        res = self.__unpack__(self.__memory__)
        if len(res) == 1:
            return res[0]
        return res

    def set(self, *args):
        """
        Change the value of the current foreign variable, given the
        'args' initializer.
        """
        self.__init__(*args)

    def __update__(self, _mem):
        type_check.parse(memory.Memory | Buffer, _mem)
        if len(_mem) != type(self).__size__:
            with errors.frame_mask:
                raise ValueError("Memory must be updated with data of the same length.")
        _mem = bytes(_mem)
        self.__memory__[:] = _mem

    @classmethod
    def __ptr_as_obj__(cls, address) -> object:
        """
        Customizable Pointer.as_object() hook.
        Allows Pointer[PyObject].as_object() to return
        an object owned by the interpreter, i.e. the
        'object' instance stored inside the pointer.
        """
        return NotImplemented

    @classmethod
    def __ptr_from_obj__(cls, tp, source):
        """
        Customizable Pointer initializing hook.
        Allows to customize pointer arguments.

        Must return a tuple of (address, ref)
        where address is the pointer's target,
        ref is a reference to keep the target
        alive. If ref is None, the pointer
        cannot be dereferenced.
        """
        return NotImplemented

    @classmethod
    def from_memory(cls, _mem):
        """
        Store foreign data of type cls into the given memory
        block.
        """
        type_check.parse(memory.Memory, _mem)
        self = cls.__new__(cls)
        self.__memory__ = _mem.get_segment(range(cls.__size__)) if len(_mem) >= cls.__size__ else _mem
        return self


class void(metaclass=ForeignData_Meta):
    """
    The 'void' type.
    Instantiating or subclassing it makes no sense, so it is disabled.

    Some placeholder methods are still implemented, for compatibility
    reasons.
    """
    __size__ = 0
    __struct_type__ = ''

    def __new__(cls, *args, **kwargs):
        raise TypeError('void cannot be instantiated.') from errors.configure(depth=1)

    def __init_subclass__(cls, **kwargs):
        raise TypeError('void cannot be subclassed.') from errors.configure(depth=1)

    @classmethod
    def __pack__(cls, *data):
        """
        Packing void yields an empty buffer.
        """
        return b""

    @classmethod
    def __unpack__(cls, buffer):
        """
        Unpacking void makes no sense.
        """
        return ()

    def as_object(self) -> tuple[object] | object:
        """
        There exists no python equivalent to void.
        ## maybe NoneType should be returned
        """
        return type(None)  # NotImplemented

    @classmethod
    def __ptr_as_obj__(cls, address) -> object:
        """
        Pointer[void].as_object() -> the address pointed to by the pointer.
        """
        return address

    @classmethod
    def __ptr_from_obj__(cls, ptr_type, source) -> tuple[int, object]:
        """
        Pointer[void] should be initialized from an integer address.
        Pointer[void] cannot be dereferenced.
        """
        return source, None


@template(ptype=ForeignData_Meta)
class Pointer(ForeignData, struct_type='P'):
    """
    Represents a pointer to a given chunk of memory.

    Pointer[T](t) -> pointer to a variable 't' of type T.

    This is the only place where the void type is accepted.
    """

    ptype: TArg[0]  # real type is type[ForeignData | void]
    """The type of data the pointer points to."""

    def __init__(self, obj):
        type_check.parse(self.ptype, obj)
        addr = obj.__memory__.address
        super(type(self), self).__init__(addr)
        self._target_mem = memory.Memory(obj.__memory__.view())

    def as_object(self):
        """
        Convert a pointer to a python object.
        Implementation may depend on the type of data pointed to,
        but default converts it to a python integer.
        """
        res = self.ptype.__ptr_as_obj__(super(type(self), self).as_object())
        if res is NotImplemented:
            return super(type(self), self).as_object()
        return res

    def deref(self):
        """
        Dereference a pointer.
        """
        if self.ptype in (void, None):
            raise TypeError("Cannot dereference void pointers.")
        c_instance = self.ptype.__new__(self.ptype)
        c_instance.__memory__ = memory.Memory(self._target_mem.view())
        return c_instance

