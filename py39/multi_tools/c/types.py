from ..functional import abstractmethod
import _ctypes
from ..errors import *
import ctypes


_SimpleCData = getattr(_ctypes, '_SimpleCData')
_CData: type = _SimpleCData.__bases__[0]


class CObject(object):
    """
    The base class for all C types. It's main purpose is to allow simple creation of other C types.

    Avoid instantiating this class directly as it will cause errors when passing instances to C functions.
    """
    __orig_type__ = None

    __slots__ = ["__data"]

    def __init__(self, data: bytes):
        """
        Instantiate a new C object, storing it's data as bytes, since they can be easily converted into
        C data.
        """
        self.__data = data

    def __init_subclass__(cls, **kwargs):
        """
        Implement subclassing. This method will not be inherited by subclasses, so sub-subclasses cannot use
        the _root subclassing parameter, and therefore cannot force their '__orig_type__' class attribute
        to be None or other than _ctypes._CData objects.
        """
        parent_cls: type = cls.__bases__[0]

        def _wrap_init_subclass(cls_, **kwds):
            if not isinstance(cls_.__orig_type__, _CData):
                raise TypeError(f"'__orig_type__': Expected type '_ctypes._SimpleCData', got '{type(cls.__orig_type__).__qualname__}' instead.")

        # make sure child classes don't inherit from __init_subclass__:
        if parent_cls.__init_subclass__ == cls.__init_subclass__:
            _wrap_init_subclass.__name__ = '__init_subclass__'
            _wrap_init_subclass.__qualname__ = f"{cls.__qualname__}.__init_subclass__"
            cls.__init_subclass__ = classmethod(_wrap_init_subclass)

        _root = False
        if '_root' in kwargs and isinstance(kwargs.get('_root'), bool):
            _root = kwargs.get('_root')

        if not _root:
            # make sure the class attribute __orig_type__ of the subclass is set:
            if cls.__orig_type__ is None:
                raise ValueError("Class attribute '__orig_type__' should be set.")
            if not (isinstance(cls.__orig_type__, type) and issubclass(cls.__orig_type__, _CData)):
                raise SimpleTypeError(type(cls.__orig_type__), 'type[_ctypes._CData]', source='__orig_type__')

    @abstractmethod
    def __c__(self, *args, **kwargs):
        """
        A method to be implemented by every C type. It should define how to
        convert their data to an actual C object. It will be used for parameter passing
        to C functions.
        """
        pass

    def _get(self):
        """
        Allows subclasses to access the bytes stored into self.
        """
        return self.__data

    __addr__ = property(lambda self: ctypes.addressof(ctypes.py_object(self)))


class CVoidPtr(CObject):
    """
    A C void*

    - Static self.from_object(): Create and return a new void* pointing to the given object.
    - self.__init__(): Create and return a new void* from the given integer address.
    """
    __orig_type__ = ctypes.c_void_p
    __slots__ = ['_ptr']

    def __init__(self, address: int):
        """
        Initialize a new C void*

        Avoid instantiating this class directly, prefer using it's static 'from_object()'.
        """
        super().__init__(address.to_bytes(8, 'big'))
        self._ptr = ctypes.c_void_p.from_address(address)

    def __c__(self, *args, **kwargs):
        return self._ptr

    address = property(lambda self: int.from_bytes(self._get(), 'big'))

    @staticmethod
    def from_object(object_):
        addr = ctypes.addressof(object_)
        return CVoidPtr(addr)


class PyObject(CObject):
    """
    A C PyObject*

    Convert an object into basically the same, but suitable for passing it as parameter
    to a C function.
    """
    __orig_type__ = ctypes.c_void_p
    __slots__ = ['_ptr']

    def __init__(self, obj):
        super().__init__(ctypes.addressof(obj).to_bytes(8, 'big'))
        self._ptr = ctypes.cast(ctypes.py_object(obj), ctypes.c_void_p)

    def __c__(self, *args, **kwargs):
        return self._ptr

    address = property(lambda self: int.from_bytes(self._get(), 'big'))


class CChar(CObject):
    __orig_type__ = ctypes.c_char

    def __init__(self, char):
        b = bytes(char, encoding='utf-8')
        limit1 = -128
        limit2 = 127
        if limit1.to_bytes(1, 'big') <= b <= limit2.to_bytes(4, 'big'):
            super().__init__(b)
            return
        raise OverflowError("Value too big.")

    def __c__(self, *args, **kwargs):
        b = self._get()
        return ctypes.c_char(b)

    @property
    def value(self):
        b = self._get()
        return str(b, encoding='utf-8')




