from .._internal import memory
from .._internal import *
from ._base import *
from .._internal.meta import *


_INTEROP_NAME = __NAME__ + '.interop2'


@scope_at(_INTEROP_NAME)
@template(atype=type[ForeignData], alen=[int, -1])
class Array(ForeignData, type='P'):
    atype: TArg[0]
    alen: TArg[1]

    __slots__ = [
        '__contents__',  # arrays keep track of their contents
        '__length__',  # and of the length
    ]

    def __init__(self, *elements):
        if self.alen >= 0:  # type: ignore
            if len(elements) > self.alen:  # type: ignore
                raise TypeError(f"Expected {self.alen} elements, got {len(elements)} instead.") from configure(depth=1)
            self.__length__: int = self.alen  # type: ignore
        else:
            self.__length__ = len(elements)

        # type_check.parse(*(self.atype for _ in elements), *elements)
        self.__contents__ = memory.Memory(len(elements) * self.atype.__size__)
        with errors.frame_mask:
            super(type(self), self).__init__(self.__contents__.address)

        for i in range(len(elements)):
            elem = elements[i]
            start = i * self.atype.__size__
            stop = start + self.atype.__size__

            if isinstance(elem, self.atype):
                c_elem: ForeignData = elem  # type: ignore
            else:
                if not isinstance(elem, tuple):
                    elem = (elem,)
                with errors.frame_mask:
                    c_elem: ForeignData = self.atype(*elem)

            self.__contents__[start:stop] = bytes(c_elem.__memory__)


    def __getitem__(self, item):
        type_check.parse(SupportsIndex, item)
        item = item.__index__()
        if item < 0:
            item += self.__length__
        if (item >= self.__length__) or (item < 0):
            raise IndexError("index out of range.") from configure(depth=1)
        return self.atype.from_memory(self.__contents__.get_segment(range(item * self.atype.__size__, (item + 1) * self.atype.__size__)))

    def __setitem__(self, key, value):
        type_check.parse(SupportsIndex, key)
        key = key.__index__()
        if key < 0:
            key += self.__length__
        if (key >= self.__length__) or (key < 0):
            raise IndexError("index out of range.") from configure(depth=1)

        if isinstance(value, self.atype):
            c_value = value
        else:
            if not isinstance(value, tuple):
                value = (value,)
            with errors.frame_mask:
                c_value = self.atype(*value)

        self.__contents__[key * self.atype.__size__:(key + 1) * self.atype.__size__] = bytes(c_value.__memory__)

    def __iter__(self):
        return _ArrayIterator(self)

    def __len__(self):
        return self.__length__

    def __repr__(self):
        return f"<C ({type(self).__name__})" + "{" + ', '.join(repr(i.as_object()) for i in self) + "}>"

    def as_object(self) -> object:
        return list(i.as_object() for i in self)


class _ArrayIterator:
    __slots__ = [
        '_array',
        '_position',
    ]

    def __init__(self, array):
        self._array = array
        self._position = 0

    def __next__(self):
        if self._position >= self._array.__length__:
            raise StopIteration
        res = self._array[self._position]
        self._position += 1
        return res

