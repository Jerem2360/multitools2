import ctypes
import _ctypes
from .._meta import *
from .._ref import reference
from .._type_check import *
import sys
from .._multidict import *
from ..errors import *


class CInstanceType(metaclass=MultiMeta):
    """
    Represent a C instance, or in other words a C object.
    This class and it's subclasses are not meant to be used as
    the C instance's type.

    C instances and C types are stored and managed independantly.

    C instances store various data, organized as following:

    """
    value = reference('_handle.value', b"", writable=False)
    """The value contained by the instance."""
    handle = reference('_handle', None, writable=False)
    """The underlying ctypes._CData instance associated to the C object."""
    ctype = reference("_type", None, writable=False)
    """The CType associated with this instance."""
    __extra__ = MultiDict({})
    """extra data that can be stored inside the instance."""

    @classmethod
    def __new__(cls, *args, **kwargs):
        """
        Create and return a new object.
        Add all keyword arguments to the extra values stored into the instance.
        """
        instance = super().__new__(cls)
        instance.__extra__ = MultiDict(kwargs)
        args = list(args)
        args.pop(0)
        args.pop(0)
        instance.__init__(*args, **kwargs)
        return instance

    def __init__(self, handle):
        """
        Create a new C object.
        """
        typecheck(handle, (self.__origin__,), target_name='handle')
        self._handle = handle

    def get(self):
        """
        Return the instance's suitable value.
        """
        return self.value

    @classmethod
    def __class_instancecheck__(cls, instance):
        return type(instance) == cls or issubclass(type(instance), cls)

    @classmethod
    def __class_subclasscheck__(cls, subclass):
        return cls in subclass.__bases__

    def __repr__(self):
        """
        Implement repr(self)
        """
        return f"<C '{self.__clsname__}' object>"


class CType(metaclass=MultiMeta):
    __c_origin__ = ctypes.py_object
    """The ctypes type the CType corresponds and should be converted to"""
    __py_origin__ = object
    """The python type the CType corresponds and should be converted to"""
    __instance_type__ = CInstanceType
    """The instance type attached to this static type"""
    __tpname__ = "PyObject*"
    """The name of the type."""
    __tpwords__ = [__tpname__]
    """The words used to represent the type"""
    __extra__ = MultiDict({})
    """Extra data that are to be stored in the class and the instance."""

    @classmethod
    def __new__(cls, *args, **kwargs):
        """
        Create and return a new instance of the corresponding instance type.
        """
        instance = cls.__instance_type__.__new__(cls.__instance_type__, *args, **kwargs)
        setattr(instance, "_type", cls)
        return instance

    def __init__(self, *args, **kwargs):
        raise TypeError("c type wasn't instantiated correctly: "
                        "use 'Ctype(*args, **kwargs)'\n")

    @classmethod
    def __class_instancecheck__(cls, instance):
        """
        Implement isinstance(instance, cls)
        """
        return isinstance(instance, cls.__instance_type__)

    @classmethod
    def __class_subclasscheck__(cls, subclass):
        """
        Implement issubclass(cls, subclass)
        """
        if subclass is None:
            return False

        if CType in subclass.__bases__ or subclass is CType:
            return True
        return False

    @classmethod
    def __class_getitem__(cls, item):
        """
        Implement cls[a, b, ...]
        Support for multiple values
        """
        if not isinstance(item, (tuple, list)):
            item = (item,)

        if item[0] == "pytype":
            return cls.__py_origin__
        elif item[0] == "ctype":
            return cls.__c_origin__
        result = cls.__detail__(*item)
        setattr(result.__instance_type__, '_type', result.__c_origin__)
        return result

    @classmethod
    def __detail__(cls, *args):
        """
        Implement cls[*args]
        Return cls by default
        """
        return cls

    @classmethod
    def __to_c__(cls, instance):
        """
        Custom C conversion if needed.
        """
        return instance.handle

    @classmethod
    def __to_py__(cls, instance):
        """
        Custom python conversion if needed.
        """
        return instance.value

    @classmethod
    def __from_c__(cls, c_instance):
        """
        Custom conversion from C if needed.
        """
        typecheck(c_instance, (cls.__c_origin__,), target_name='c_instance')
        return cls.__instance_type__(c_instance)


CType.from_param = classmethod(lambda cls: cls.__c_origin__)
CInstanceType.from_param = lambda self: self._handle


class _WithSign(metaclass=MultiMeta):
    signed = reference('__extra__.signed', True, writable=False)


class _WithByteOrder(metaclass=MultiMeta):
    byteorder = reference('__extra__.byteorder', 'big', writable=False)


class CIntInstance(CInstanceType, metaclass=MultiMeta):
    signed = reference('type_type.signed', True)
    byteorder = reference('type_type.byteorder', 'big')

    def __init__(self, value):
        super().__init__(self.__origin__(value))


class Int(CType, _WithSign, _WithByteOrder, metaclass=MultiMeta):
    __c_origin__ = ctypes.c_int
    __py_origin__ = int
    __instance_type__ = CIntInstance

    @classmethod
    def __detail__(cls, *args):
        """
        Int[signed: bool, byteorder: Literal['big', 'little']] -> type[Int]
        """
        if len(args) != 2:
            return cls
        result = cls
        result.signed = args[0]
        result.byteorder = args[1]
        result.__c_origin__ = ctypes.c_int if result.signed else ctypes.c_uint
        return result


class _WithLength(metaclass=MultiMeta):
    long = reference('__extra__.long', False, writable=False)


class CLongInstance(CInstanceType, metaclass=MultiMeta):
    long = reference('type_type.long', False)

    def __init__(self, value):
        super().__init__(self.__origin__(value))


class Long(Int, _WithLength, metaclass=MultiMeta):
    __c_origin__ = ctypes.c_long
    __py_origin__ = int
    __instance_type__ = CLongInstance

    # noinspection PyMethodOverriding
    @classmethod
    def __detail__(cls, *args):
        """
        Long[signed: bool, byteorder: Literal['big', 'little'], long: bool] -> type[Long]
        """
        if len(args) != 3:
            return cls
        result = cls
        result.signed = args[0]
        result.byteorder = args[1]
        result.long = args[2]
        if result.long:
            result.__c_origin__ = ctypes.c_longlong if result.signed else ctypes.c_ulonglong
        else:
            result.__c_origin__ = ctypes.c_long if result.signed else ctypes.c_ulong

        return result


class CShortInstance(CInstanceType, metaclass=MultiMeta):

    def __init__(self, value):
        super().__init__(self.__origin__(value))


class Short(Int, metaclass=MultiMeta):
    __c_origin__ = ctypes.c_short
    __instance_type__ = CShortInstance


class CSize_tInstance(CInstanceType, metaclass=MultiMeta):

    def __init__(self, value):
        super().__init__(self.__origin__(value))


class Size_t(Int[False, 'big'], metaclass=MultiMeta):
    __c_origin__ = ctypes.c_size_t
    __instance_type__ = CSize_tInstance

    @classmethod
    def __detail__(cls, *args):
        """
        default
        """
        return cls


class CSsize_tInstance(CInstanceType, metaclass=MultiMeta):

    def __init__(self, value):
        # noinspection PyArgumentList
        super().__init__(self.__origin__(value))


class SSize_t(Int[True, 'big'], metaclass=MultiMeta):
    __c_origin__ = ctypes.c_ssize_t
    __instance_type__ = CSsize_tInstance

    @classmethod
    def __detail__(cls, *args):
        """
        default
        """
        return cls


class CFloatInstance(CInstanceType, metaclass=MultiMeta):
    __clsname__ = "float"
    __origin__ = ctypes.c_float

    def __init__(self, value):
        super().__init__(self.__origin__(value))


class Float(CType, metaclass=MultiMeta):
    __c_origin__ = ctypes.c_float
    __py_origin__ = float
    __instance_type__ = CFloatInstance


class CDoubleInstance(CInstanceType, metaclass=MultiMeta):
    __clsname__ = "double"
    __origin__ = ctypes.c_double

    def __init__(self, value):
        super().__init__(self.__origin__(value))


class Double(Float, _WithLength, metaclass=MultiMeta):
    __c_origin__ = ctypes.c_double
    __instance_type__ = CDoubleInstance

    @classmethod
    def __detail__(cls, *args):
        """
        Double[long: bool] -> Type[Double]
        """
        if len(args) != 1:
            return cls
        result = cls
        result.long = args[0]
        result.__c_origin__ = ctypes.c_longdouble if result.long else ctypes.c_double

        return result


class CBoolInstance(CInstanceType, metaclass=MultiMeta):
    __clsname__ = "boolean"
    __origin__ = ctypes.c_bool

    def __init__(self, value):
        super().__init__(self.__origin__(value))


class Bool(CType, metaclass=MultiMeta):
    __c_origin__ = ctypes.c_bool
    __py_origin__ = bool
    __instance_type__ = CBoolInstance


class _WithEncoding(metaclass=MultiMeta):
    encoding = reference('__extra__.encoding', sys.getdefaultencoding())


class CStrInstance(CInstanceType, metaclass=MultiMeta):
    __clsname__ = "const char*"
    __origin__ = ctypes.c_char_p
    encoding = reference('__extra__.encoding', sys.getdefaultencoding())

    def __init__(self, value):
        super().__init__(self.__origin__(bytes(value, encoding=self.encoding)))


class Str(CType, _WithEncoding, metaclass=MultiMeta):
    __c_origin__ = ctypes.c_char_p
    __py_origin__ = str
    __instance_type__ = CStrInstance

    def __new__(cls, *args, **kwargs):
        # noinspection PyTypeChecker
        self = super().__new__(cls, *args, **kwargs)
        self.encoding = cls.encoding
        return self

    @classmethod
    def __detail__(cls, *args):
        """
        Str[encoding: str] -> type[Str]
        """
        if len(args) != 1:
            return cls
        result = cls
        typecheck(args[0], (str,), target_name='encoding')
        result.encoding = args[0]
        return result

    @classmethod
    def __to_py__(cls, instance):
        return str(instance.value, encoding=cls.encoding)


class CCharInstance(CInstanceType, metaclass=MultiMeta):
    __clsname__ = "char"
    __origin__ = ctypes.c_char
    encoding: str = sys.getdefaultencoding()

    def __init__(self, value):
        super().__init__(self.__origin__(value))


class Char(CType, _WithEncoding, metaclass=MultiMeta):
    __c_origin__ = ctypes.c_char
    __py_origin__ = str
    __instance_type__ = CCharInstance

    def __new__(cls, *args, **kwargs):
        # noinspection PyTypeChecker
        instance = super().__new__(cls, *args, **kwargs)
        instance.encoding = cls.encoding
        return instance

    @classmethod
    def __detail__(cls, *args):
        """
        Char[encoding: str] -> Type[Char]
        """
        if len(args) != 1:
            return cls
        result = cls
        typecheck(args[0], (str,), target_name='encoding')
        result._encoding = args[0]
        return result

    @classmethod
    def __to_py__(cls, instance):
        return str(instance.value, encoding=cls.encoding)


class NullInstance(CInstanceType, metaclass=MultiMeta):
    __clsname__ = "NULL"
    __origin__ = type(None)

    def __init__(self, *args, **kwargs):
        super().__init__(None)

    # absent from stubs for type checking compatibility: they mustn't be recognized by the former as valid.
    def __call__(self, *args, **kwargs):
        raise NullReferenceError("NULL reference.")

    def __getattr__(self, item):
        raise NullReferenceError("NULL reference")

    def __repr__(self):
        return "NULL"

    def __bytes__(self):
        return b"\x00"

    def __pow__(self, power, modulo=None):
        raise NullReferenceError("NULL reference.")

    def __itruediv__(self, other):
        raise NullReferenceError("NULL reference.")

    def __rtruediv__(self, other):
        raise NullReferenceError("NULL reference.")

    def __truediv__(self, other):
        raise NullReferenceError("NULL reference.")

    def __imul__(self, other):
        raise NullReferenceError("NULL reference.")

    def __rmul__(self, other):
        raise NullReferenceError("NULL reference.")

    def __invert__(self):
        raise NullReferenceError("NULL reference")

    def __add__(self, other):
        raise NullReferenceError("NULL reference")

    def __mul__(self, other):
        raise NullReferenceError("NULL reference")

    def __abs__(self):
        raise NullReferenceError("NULL reference")

    def __ceil__(self):
        raise NullReferenceError("NULL reference")

    def __isub__(self, other):
        raise NullReferenceError("NULL reference")

    def __float__(self):
        return 0.0

    def __rsub__(self, other):
        raise NullReferenceError("NULL reference")

    def __sub__(self, other):
        raise NullReferenceError("NULL reference")

    def __neg__(self):
        raise NullReferenceError("NULL reference")

    def __iadd__(self, other):
        raise NullReferenceError("NULL reference")

    def __getitem__(self, item):
        raise NullReferenceError("NULL reference")

    def __len__(self):
        return 0

    def __hex__(self):
        return 0x0

    def __radd__(self, other):
        raise NullReferenceError("NULL reference")

    def __str__(self):
        raise NullReferenceError("NULL reference")

    def __rshift__(self, other):
        raise NullReferenceError("NULL reference")

    def __int__(self):
        return 0

    def __iter__(self):
        raise NullReferenceError("NULL reference")

    def __bool__(self):
        return False

    def __aiter__(self):
        raise NullReferenceError("NULL reference")

    def __floordiv__(self, other):
        raise NullReferenceError("NULL reference")

    def __await__(self):
        raise NullReferenceError("NULL reference")


class Null(CType, metaclass=MultiMeta):
    """
    type(NULL)
    """
    __c_origin__ = type(None)
    __py_origin__ = type(None)
    __instance_type__ = NullInstance

    @classmethod
    def __to_py__(cls, instance):
        return None

    @classmethod
    def __to_c__(cls, instance):
        return None

    @classmethod
    def __from_c__(cls, c_instance):
        typecheck(c_instance, (type(None),), target_name='c_instance')
        return NullInstance()


class CBytesInstance(CInstanceType, metaclass=MultiMeta):
    __clsname__ = "char*"
    __origin__ = ctypes.c_byte

    def __init__(self, value):
        super().__init__(self.__origin__(value))


class Bytes(CType, _WithSign, metaclass=MultiMeta):
    __c_origin__ = ctypes.c_byte
    __py_origin__ = bytes
    __instance_type__ = CBytesInstance

    @classmethod
    def __detail__(cls, *args):
        """
        Bytes[signed: bool] -> Type[Bytes]
        """
        if len(args) != 1:
            return cls
        result = cls
        result.signed = args[0]
        result.__c_origin__ = ctypes.c_byte if result.signed else ctypes.c_ubyte
        return result


class CPtrInstance(CInstanceType, metaclass=MultiMeta):
    __origin__ = ctypes.c_void_p
    __clsname__ = "void*"

    def __init__(self, address):
        self.__extra__.address = address
        super().__init__(self.__origin__(address))


class Ptr(CType, metaclass=MultiMeta):
    __c_origin__ = ctypes.pointer
    __py_origin__ = reference('type.__py_origin__', object, writable=False)
    __instance_type__ = CPtrInstance

    type = reference('__extra__.type', None)

    @classmethod
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        self.__extra__.address = 0
        # noinspection PyUnresolvedReferences
        self.__clsname__ = "void*" if cls.type is None else f"{cls.type.__instance_type__.__clsname__}*"
        return self

    @classmethod
    def __detail__(cls, *args):
        """
        Ptr[type: type[CType]] -> type[Ptr]
        """
        if len(args) != 1:
            return cls
        result = cls
        typecheck(args[0], (type,), target_name="type",
                  check_func=lambda: isinstance(args[0], type) and issubclass(args[0], CType))
        result.type = args[0]
        result.__c_origin__ = ctypes.POINTER(args[0].__c_origin__)
        return result

    @classmethod
    def addressof(cls, obj):
        if isinstance(obj, CInstanceType):
            addr = ctypes.addressof(obj.handle)
        else:
            addr = ctypes.addressof(ctypes.py_object(obj))
        return cls(addr)

    @classmethod
    def __to_c__(cls, instance):
        return instance.handle

    @classmethod
    def __to_py__(cls, instance):
        return instance.__extra__.get('address')

