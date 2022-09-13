import ctypes
import struct

from ._base_type import CTypeMeta, CType
from ._mem import Memory
from ..errors._errors import err_depth, ATTR_ERR_STR
from .._parser import parse_args


def _build_struct_struct_type(types):
    res = ''
    for tp in types:
        if '*' in tp.__type__:
            return '*'
        res += tp.__type__

    return res


def _fields_from_annotations(annot):
    res = {}
    offset = 0
    for k, v in annot.items():
        res[k] = v, offset
        offset += v.__size__

    return res


class StructMeta(CTypeMeta):
    def __new__(mcs, name, bases, np):
        np['__simple__'] = Ellipsis
        cls = super().__new__(mcs, name, bases, np)
        cls.__fields__ = _fields_from_annotations(cls.__annotations__)
        cls.__type__ = _build_struct_struct_type(tuple(cls.__fields__.values()))
        for k in cls.__fields__:
            if hasattr(cls, k):
                raise err_depth(TypeError, "Struct field default values are not supported.")
        cls.__ctypes_struct__ = None
        return cls

    @property
    def __simple__(cls):
        if cls.__ctypes_struct__ is None:
            _fields = []
            for k, v in cls.__fields__:
                tp, offset = v
                if not hasattr(tp, '__simple__'):
                    continue
                _fields.append((k, tp.__simple__))

            _fields = tuple(_fields)

            class _Struct(ctypes.Structure):
                _fields_ = _fields

            cls.__ctypes_struct__ = _Struct
        return cls.__ctypes_struct__

    def __repr__(cls):
        return f"<C typedef struct '{cls.__name__}'>"


class Struct(CType, metaclass=StructMeta):

    def __init__(self, *values):
        if type(self).__type__ != '*':
            self._data = Memory(struct.calcsize(type(self).__type__))
            self._data[:] = struct.pack(type(self).__type__, *values)
            return

        struct_t = type(self).__simple__
        ct_instance = struct_t(*values)
        self._data = Memory(ct_instance)

    def __getattr__(self, item):
        if item in type(self).__fields__:
            tp, offset = type(self).__fields__[item]

            # lookup the memory we are interested in:
            view = self._data.view()[offset:offset+tp.__size__]
            ob_mem = Memory(view)

            # create the instance based on the existing memory:
            ob = tp.__new__()
            ob._data = ob_mem
            return ob
        raise err_depth(AttributeError, ATTR_ERR_STR.format(type(self).__name__, item), depth=1)

    def __setattr__(self, key, value):
        parse_args((key, value), str, CType, depth=1)
        if key in type(self).__fields__:
            tp, offset = type(self).__fields__[key]

            # value must have the right type:
            parse_args((value,), tp, depth=1)
            # update directly the memory with the correct data:
            self._data.view()[offset:offset+tp.__size__] = value._data.view()
            return
        return super().__setattr__(key, value)

    def __repr__(self):
        struct_args = '{' + ', '.join(self._args) + '}'
        return f"<C struct {type(self).__name__}{struct_args}>"
