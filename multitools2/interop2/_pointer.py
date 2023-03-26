import struct

from .._internal.meta import *
from .._internal import *
from ._base import *


_INTEROP_NAME = __NAME__ + '.interop2'


"""@Singleton
@scope_at(_INTEROP_NAME)
@final
class nullptr(ForeignData, type='P'):

    def __init__(self):
        super(type(self), self).__init__(0)

    def deref(self):
        raise memory.AccessViolationError(0, memory.SegvType.read) from configure(depth=1)

    def as_object(self):
        return 0
    
    def set(self, *args):
        """


@scope_at(_INTEROP_NAME)
@template(ptype=type[ForeignData | void])
class Pointer(ForeignData, type='P'):
    ptype: TArg[0]
    __null__ = None

    def __init__(self, source):
        impl = self.ptype.__pointer_from_object__(source)
        if impl is NotImplemented:
            type_check.parse(self.ptype, source)
            addr = source.__memory__.address
        else:
            if not type_check.parse(SupportsIndex, impl, raise_=False):
                raise TypeError(f"{self.ptype.__name__}.__pointer_from_object__ must return an integer address.") from configure(depth=1)
            addr = impl

        with errors.frame_mask:
            super(type(self), self).__init__(addr)

    def __add__(self, other):
        res = type(self).__new__(type(self))
        type(self).__pack__(self.__unpack__(self.__memory__) + other, buffer=res.__memory__)
        return res

    def __radd__(self, other):
        return other + self.__unpack__(self.__memory__)

    def __iadd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        res = type(self).__new__(type(self))
        type(self).__pack__(self.__unpack__(self.__memory__) - other, buffer=res.__memory__)
        return res

    def __rsub__(self, other):
        res = type(self).__new__(type(self))
        return other - self.__unpack__(self.__memory__)

    def __isub__(self, other):
        return self.__sub__(other)

    def deref(self):
        address = self.__unpack__(self.__memory__)
        with errors.frame_mask:  # AccessViolation may occur
            mem = memory.Memory.at_address(address, self.ptype.__size__)  # type: ignore
        return self.ptype.from_memory(mem)

    def as_object(self):
        impl = self.ptype.__pointer_as_object__(self)
        if impl is NotImplemented:
            return self.__unpack__(self.__memory__)
        return impl

    def set(self, source):
        impl = self.ptype.__pointer_from_object__(source)

        if impl is NotImplemented:
            # type_check.parse(memory.Memory | ForeignData, source)
            if isinstance(source, memory.Memory):
                addr = source.address
            elif isinstance(source, self.ptype):
                addr = source.__memory__.address

            elif isinstance(source, ForeignData):
                raise TypeError(f"{type(self).__name__} cannot point to '{type(source).__name__}' instances.")
            else:
                with errors.frame_mask:
                    addr = self.ptype(source).__memory__.address

        else:
            if not type_check.parse(SupportsIndex, impl, raise_=False):
                raise TypeError(f"{self.ptype.__name__}.__pointer_from_object__ must return an integer address.") from configure(depth=1)

            addr = impl

        self.__pack__(addr, buffer=self.__memory__.view())

    @classmethod
    @property
    def null(cls):
        if cls.__null__ is None:
            cls.__null__ = cls.__new__(cls)
            cls.__pack__(0, buffer=cls.__null__.__memory__)
        return cls.__null__

