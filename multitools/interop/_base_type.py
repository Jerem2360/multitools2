import copy
import struct
import sys


import _ctypes

from ..errors import err_depth
from .._meta import *
from ._mem import Memory
from .._typeshed import *
from .._parser import *
from .._singleton import Singleton

from ..interface import SupportsIndex


"""
class PyObject(Struct):
#ifdef Py_TRACE_REFS  (NOT supported)
    _ob_next: Pointer[PyObject]
    _ob_prev: Pointer[PyObject]
#endif
    ob_refcnt: SSize_t
    ob_type: Pointer[PyTypeObject]
"""


@Singleton
class NULL:
    """
    Basic singleton that compares equal to zero and to null pointers.
    Helpful when looking for null pointers and python object pointers.
    """
    def __eq__(self, other):
        if other == 0:
            return True
        return super(type(self), self).__eq__(other)

    def __ne__(self, other):
        if other == 0:
            return False
        return super(type(self), self).__ne__(other)

    def __index__(self):
        return 0

    def __int__(self):
        return 0

    def __float__(self):
        return 0.0

    def __complex__(self):
        return 0j


__TYPE__ = '__type__'
__CTYPE_LE__ = '__ctype_le__'
__CTYPE_BE__ = '__ctype_be__'


class CTypeMeta(MultiMeta):
    """
    Base metaclass for all C data types and structures.
    Provides default implementations for customizable fields and
    implements __repr__().
    """
    def __new__(mcs, name, bases, np, **kwargs):
        custom_simple = Ellipsis
        if '__simple__' in np:
            custom_simple = copy.copy(np['__simple__'])
            del np['__simple__']

        _cname = np.get('__c_name__', name)
        if _cname in (None, Ellipsis):
            _cname = name

        name = _cname

        parse_args((custom_simple,), type(Ellipsis) | type(_ctypes._SimpleCData) | None, depth=1)

        cls = super().__new__(mcs, name, bases, np, **kwargs)

        cls._SimpleType = None
        if custom_simple is not Ellipsis:
            custom_simple.__name__ = cls.__name__ + '._SimpleType'
            custom_simple.__qualname__ = cls.__qualname__ + '._SimpleType'
            custom_simple.__module__ = cls.__module__
            cls._SimpleType = custom_simple
        cls._is_basetype = False
        if hasattr(cls, __TYPE__):
            cls.__byteorder__ = '@'
            cls._little_endian_t = None
            cls._big_endian_t = None
            if cls.__type__ == '*' and cls._SimpleType is None:
                raise err_depth(TypeError, "A C type that relies on the ctypes module must provide a source type.",
                                depth=1)

            if cls.__type__ == '*':
                cls.__size__ = _ctypes.sizeof(cls._SimpleType)
            else:
                cls.__size__ = struct.calcsize(cls.__type__)
        else:
            cls._is_basetype = True
        return cls

    def __repr__(cls):
        return f"<C type '{cls.__name__}'>"

    def __mul__(cls, other):
        """
        CType * n -> a C type representing arrays of n CType instances.
        Same as in ctypes, except we use our own data types.
        """
        parse_args((other,), SupportsIndex, depth=1)
        other = other.__index__()
        from . import _array
        return _array.Array[cls, other]

    def with_byteorder(cls, byteorder):
        """
        Return the same type, but with a changed byteorder.
        """
        if byteorder == 'little':
            if cls._little_endian_t is not None:
                return cls._little_endian_t

            if cls.__type__ == '*':
                res = cls.dup_shallow()
                if not hasattr(cls._SimpleType, __CTYPE_LE__):
                    cls._little_endian_t = res
                    res._little_endian_t = res
                    return cls._little_endian_t
                res._SimpleType = cls._SimpleType.__ctype_le__
                cls._little_endian_t = res
                res._little_endian_t = res
                return cls._little_endian_t

            res = cls.dup_shallow()
            res.__byteorder__ = '<'
            cls._little_endian_t = res
            res._little_endian_t = res
            return cls._little_endian_t

        if cls._big_endian_t is not None:
            return cls._big_endian_t

        if cls.__type__ == '*':
            res = cls.dup_shallow()
            if not hasattr(cls._SimpleType, __CTYPE_BE__):
                cls._big_endian_t = res
                res._big_endian_t = res
                return cls._big_endian_t
            res._SimpleType = cls._SimpleType.__ctype_be__
            cls._big_endian_t = res
            res._big_endian_t = res
            return cls._big_endian_t
        res = cls.dup_shallow()
        res.__byteorder__ = '>'
        cls._big_endian_t = res
        res._big_endian_t = res
        return cls._big_endian_t

    def __hash__(cls):
        return id(cls)

    @property
    def __ctype__(cls):
        """
        The type in struct module format.
        """
        return cls.__byteorder__ + cls.__type__

    @property
    def __simple__(cls):
        """
        For portability with ctypes.
        A basic ctypes version of this type, in form of a _ctypes._SimpleCData subclass,
        or a _ctypes.Structure subclass.
        This is only defined if the equivalent of this type in ctypes inherits from
        _ctypes._SimpleCData or _ctypes.Structure .
        If overridden, this must be set to a subclass of _ctypes._SimpleCData or _ctypes.Structure, None if
        the type does not support __simple__, or Ellipsis '...' which maintains the default
        behaviour; otherwise TypeError is raised.
        """
        if hasattr(cls, '_SimpleType') and cls._SimpleType is not None:
            return cls._SimpleType

        _supports_byteorder = getattr(cls, '__supports_byteorder__', False)
        _name = getattr(cls, '__simple_name__', cls.__name__ + '._SimpleType')
        _type = getattr(cls, '__simple_type__', cls.__type__)
        # print(_type)

        class SimpleType(_ctypes._SimpleCData):
            _type_ = _type
        if _supports_byteorder:
            SimpleType.__ctype_le__ = cls.with_byteorder('little').__simple__
            SimpleType.__ctypes_be__ = cls.with_byteorder('big').__simple__
        SimpleType.__qualname__ = cls.__qualname__.replace(cls.__name__, _name)
        SimpleType.__name__ = _name.split('.')[-1]
        SimpleType.__module__ = cls.__module__

        expected = struct.calcsize(cls.__ctype__)
        got = _ctypes.sizeof(SimpleType)
        if got != expected:
            raise err_depth(SystemError, f"Invalid size for type '{cls.__name__}': expected {expected}, got {got} instead.", depth=1)

        cls._SimpleType = SimpleType
        return cls._SimpleType

    def _map_fields(cls):
        if cls.__type__ == '*':
            fields = []
            if not hasattr(cls, '__fields__'):
                return ()
            for k, v in cls.__fields__:
                try:
                    fields.append((k, v.__simple__))  # actually, 'Struct' should support __simple__
                except AttributeError:
                    raise err_depth(TypeError, "Structure fields must be of simple types or structure types.", depth=2)
            return tuple(fields)
        return ()


class CType(metaclass=CTypeMeta):
    """
    Common base class for all C types.
    C types represent data types that are present in the C and C++
    languages, and serve the purpose of being passed as arguments
    to external functions, from executables such as .dll or .so
    files.

    In a C type's class body, multiple variables can be overridden:

    - __type__ must be set to the struct format for the type or '*' if not supported.
    - __simple__ allows to specify which ctypes type we rely on when __type__ is '*'
    - __supports_byteorder__ allows to specify if the type depends on the byteorder. Defaults to False.
    - __simple_name__ gives an optional custom name for the __simple__ attribute.
    - __simple_type__ optionally provides an accurate struct format for the type if possible and in case __type__ is not accurate.

    Note that upon class creation, __simple__ is copied and then stored as an object.
    If __supports_byteorder__ is False, with_byteorder() will return an exact copy of cls.

    Overriding the __init__ constructor of a CType subclass requires calling the __init__ constructor
    of the super class.

    These C types are made portable with the ctypes module by their class attribute __simple__
    and their instance method __to_ctypes__()

    __simple__, if supported, is a _ctypes._SimpleCData subclass that is equivalent to this C type.

    The __to_ctypes__() instance method, returns a _ctypes._SimpleCData instance bound to the same
    memory block as the current instance, and of the corresponding ctypes type.
    """
    def __new__(cls, *args, **kwargs):
        # C instances only have one attribute: a view on their assigned memory block called _data.
        if cls._is_basetype:
            raise err_depth(TypeError, "Abstract base class.", depth=1)

        self = super().__new__(cls)
        self._args = ()
        return self

    def __init__(self, *values):
        # positional arguments are passed in either to struct.pack or to the constructor of the ctypes type.

        if type(self).__type__ == '*':  # if the type relies on the ctypes module, wrap the ctypes instance
            try:
                self._data = Memory(type(self).__simple__(*values))
            except AttributeError:  # the type does not support __simple__, then it's a structure.
                class _Struct(_ctypes.Structure):
                    _fields_ = type(self)._map_fields()
                self._data = Memory(_Struct(*values))
            except:
                raise err_depth(sys.exc_info()[0], *sys.exc_info()[1].args, depth=1) from None

        else:

            self._data = Memory(struct.calcsize(type(self).__ctype__))
            if len(values) != len(type(self).__type__):
                raise err_depth(ValueError, f"Expected {len(type(self).__type__)} initializer arguments.", depth=1)

            if len(values) > 0:
                self._data[:] = struct.pack(type(self).__ctype__, *values)
        self._args = values

    def __repr__(self):
        return f"<C {type(self).__name__}({', '.join(repr(arg) for arg in self._args)})>"

    def get_data(self):
        return bytes(self._data.view()[:])

    def __to_ctypes__(self):
        """
        Default implementation.
        Returns None if cls does not support __simple__.
        Otherwise, it calls the from_buffer() method of cls.__simple__
        and returns its result.
        """
        if self.__type__ == '*':
            return self._data.obj  # the type wraps a ctypes type, so return the original ctypes instance.
        try:
            return type(self).__simple__.from_buffer(self._data.view())  # we own our memory, return a new ctypes instance.
        except AttributeError:
            return None

    @classmethod
    def __from_ctypes__(cls, *values):
        return cls(*((val.value if isinstance(val, SimpleCData) else val) for val in values))

    @property
    def __address__(self):
        return self._data.address

