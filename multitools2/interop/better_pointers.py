import gc
import os
import sys
import time

from ._basis import *
from .._internal.meta import *
from . import _ctypes_link

FLAGS_HAVE_GC = (1 << 14)
"""
Pointer and array implementations.

dereferencing a python object pointer requires the object to be tracked
by the current interpreter's gc. Otherwise, this will yield the address itself.
"""


def _obj_at_address(address):
    if not address:  # don't waste time for null pointers
        return 0

    print(gc.get_count())
    for obj in gc.get_objects():
        if id(obj) == address:
            return obj
        if isinstance(obj, dict):
            print()
            print("==>", obj)
            print()
            for _obj in gc.get_referrers(obj):
                if isinstance(_obj, dict):
                    print(type(_obj), obj, _obj)
                    for k, v in _obj.copy().items():
                        if (address == id(k)) or (address == id(v)):
                            print("there:", k, v)
    raise ReferenceError("No object found.")


from multitools2._internal import runtime


print(runtime.get_file_directory())


@template(ptype=ForeignData_Meta)
class Pointer(ForeignData, struct_type='P'):
    ptype: TArg[0]

    def __init__(self, obj):
        type_check.parse(self.ptype, obj)
        with errors.frame_mask:
            super(type(self), self).__init__(obj.__memory__.address)

        self.__target__ = obj


@template(atype=ForeignData_Meta, asize=[int, -1])
class Array(ForeignData, struct_type='P'):
    atype: TArg[0]
    asize: TArg[1]


    def __init__(self, *elems):
        etypes = tuple(self.atype for e in elems)
        type_check.parse(*etypes, *elems)

        if (self.asize > 0) and (len(elems) != self.asize):
            raise TypeError(f"Expected {self.asize} elements for array.")

        size = self.atype.__size__ * len(elems)

        self.__target__ = memory.Memory(size)

        with errors.frame_mask:
            super(type(self), self).__init__(self.__target__.address)

    def __getitem__(self, item):
        type_check.parse(SupportsIndex, item)
        item = item.__index__()

        offset = item * self.atype.__size__
        sz = self.atype.__size__

        data = self.__memory__[offset:offset+sz]

        mem = memory.Memory(sz)
        mem[:] = data

        return self.atype.from_memory(mem)

