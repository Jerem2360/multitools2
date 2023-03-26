import ctypes
import struct
import sys

from .._internal.meta import *
from .._internal import *
from .._internal.errors import *
from ._basis import *
from ._integers import *
from ._ctypes_link import *


def _deref(ptr, struct_type) -> memory.Memory | tuple[memory.Memory, ...] | None:
    import ctypes

    if len(struct_type) > 1:
        before = ''
        res = []
        for char in struct_type:
            if len(before):
                res.append(_deref(ptr + struct.calcsize(before), char))
            else:
                res.append(_deref(ptr, char))
            before += char
        return tuple(res)

    match struct_type:
        case 'P':
            return memory.Memory(ctypes.c_void_p.from_address(ptr))
        case 'c':
            return memory.Memory(ctypes.c_char.from_address(ptr))
        case 'b':
            return memory.Memory(ctypes.c_byte.from_address(ptr))
        case 'B':
            return memory.Memory(ctypes.c_ubyte.from_address(ptr))
        case '?':
            return memory.Memory(ctypes.c_bool.from_address(ptr))
        case 'h':
            return memory.Memory(ctypes.c_short.from_address(ptr))
        case 'H':
            return memory.Memory(ctypes.c_ushort.from_address(ptr))
        case 'i':
            return memory.Memory(ctypes.c_int.from_address(ptr))
        case 'I':
            return memory.Memory(ctypes.c_uint.from_address(ptr))
        case 'l':
            return memory.Memory(ctypes.c_long.from_address(ptr))
        case 'L':
            return memory.Memory(ctypes.c_ulong.from_address(ptr))
        case 'f':
            return memory.Memory(ctypes.c_float.from_address(ptr))
        case 'd':
            return memory.Memory(ctypes.c_double.from_address(ptr))
        case 'n':
            return memory.Memory(ctypes.c_ssize_t.from_address(ptr))
        case 'N':
            return memory.Memory(ctypes.c_size_t.from_address(ptr))
        case 'q':
            return memory.Memory(ctypes.c_longlong.from_address(ptr))
        case 'Q':
            return memory.Memory(ctypes.c_ulonglong.from_address(ptr))



@Singleton
class nullptr:
    """
    Special pointer of type nullptr_t. Compares equal to any Pointer
    object of value 0.
    """


# print(dir(nullptr))


"""def _ptr_to_memory(mem, _ptype):
    ""
    Internal helper to create a pointer targeting
    a given memory block.
    ""
    ptr = Pointer[_ptype].__new__(Pointer[_ptype])
    ptr._ref = _ptype.__new__(_ptype)
    ptr._ref.__memory__ = mem
    ForeignData.__init__(ptr, mem.address)
    return ptr"""

"""
def validate_address(address):
    ""
    Return whether the given memory address can be read.
    ""
    if address < (256 ** 4):   # addresses of 4 bytes or fewer are usually not readable
        return False

    to_test = ctypes.cast(ctypes.c_void_p(address), ctypes.POINTER(ctypes.c_char))
    temp = ctypes.create_string_buffer(0, 1)

    try:
        ctypes.cdll.msvcrt.memcpy(temp, to_test, 1)  # we use memcpy to trigger an eventual access violation
    except OSError as e:
        msg = e.args
        if (len(msg) > 0) and (isinstance(msg[0], str)) and (msg[0].startswith('exception: access violation')):
            return False

    return True"""


@template(ptype=ForeignData_Meta)
class Pointer(ForeignData, struct_type='P'):
    ptype: TArg[0]

    def __new__(cls, *args, **kwargs) -> Pointer:
        """
        Create and return a new pointer.
        """
        if len(args) > 0:
            targ = cls.ptype.__ptr_from_obj__(cls, args[0], **kwargs)
            if (targ is not NotImplemented) and (targ[1] is None) and (targ[0] == 0):
                return nullptr  # type: ignore
        res = ForeignData.__new__(cls)
        res._ref = None
        return res

    def __init__(self, target, **kwargs):
        """
        Initialize a pointer instance.
        By default, the argument is the foreign instance the pointer should point to.
        If the pointer type defines an __ptr_from_obj__ class method, the behaviour is modified,
        """
        targ = self.ptype.__ptr_from_obj__(type(self), target, **kwargs)
        if targ is not NotImplemented:
            addr, self._ref = targ
        else:
            type_check.parse(ForeignData, target)
            self._ref = target
            addr = target.__memory__.address

        super(type(self), self).__init__(addr)

    def __eq__(self, other):
        """
        Pointer == Pointer : True if same type AND same value
        Pointer == integer : True if same value
        Pointer == nullptr : True if Pointer == 0
        """
        if isinstance(other, Pointer):
            return (other.ptype is self.ptype) and (other.as_object() == super(type(self), self).as_object())
        if isinstance(other, SupportsIndex):
            return other.__index__() == super(type(self), self).as_object()
        if other is nullptr:
            return super(type(self), self).as_object() == 0
        raise TypeError(TYPE_ERR.format('Pointer | SupportsIndex', type(other).__name__)) from configure(depth=1)

    def __repr__(self):
        if super(type(self), self).as_object() == 0:
            if self.ptype is void:
                return 'nullptr'
            return f'({type(self).__name__})nullptr'
        if self.ptype is not void:
            return f"({type(self).__name__}){hex(super(type(self), self).as_object())}"  # type: ignore
        return super(type(self), self).__repr__()

    def as_object(self):
        res = self.ptype.__ptr_as_obj__(self)
        if res is NotImplemented:
            res = super(type(self), self).as_object()
        return res

    def deref(self):
        """
        Dereference a pointer.
        Access violations are managed and are translated to AccessViolationError.
        'void' pointers cannot be dereferenced.
        """
        if self._ref is None:
            if not self.ptype.__size__:
                raise TypeError(f"{type(self).__name__} instance cannot be dereferenced.") from configure(depth=1)

            addr = super(type(self), self).as_object()

            access = validate_address(addr)
            if access:
                raise AccessViolationError(addr, access) from configure(depth=1)

            self._ref = self.ptype.from_memory(_deref(super(type(self), self).as_object(), self.ptype.__struct_type__))
        return self._ref

    @classmethod
    def from_memory(cls, _mem):
        """
        Store a pointer instance in the given memory block.
        """
        self = super(cls, cls).from_memory(_mem)
        self._ref = None
        return self
# print(Pointer[Int].__new__(Pointer[Int]) == nullptr)


@template(atype=ForeignData_Meta, length=[int, -1])
class Array(ForeignData, struct_type='P'):
    atype: TArg[0]
    length: TArg[1]

    def __init__(self, *elements):
        self._ref = memory.Memory(self.atype.__size__ * self.length)
        super(type(self), self).__init__(self._ref.address)
        data = struct.pack(self.atype.__struct_type__, *elements)
        self._ref[:] = data

    def __getitem__(self, item):
        return self.atype.from_memory(self._ref.get_segment(range(item * self.atype.__asize__, (item + 1) * self.atype.__size__)))

    def __setitem__(self, key, value):
        self._ref[key * self.atype.__asize__:(key + 1) * self.atype.__size__] = value.__memory__[:]


