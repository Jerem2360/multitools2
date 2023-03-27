from .._meta import MultiMeta
from ..errors import _errors
from .._typeshed import *
import ctypes


__INDEX__ = '__index__'
__FLOAT__ = '__float__'
__BOOL__ = '__bool__'


def _instance_has_method(obj, name):
    return hasattr(obj, name) and isinstance(getattr(obj, name), (Method, MethodWrapper))

def _class_has_method(cls, name):
    return hasattr(cls, name) and isinstance(getattr(cls, name), (Function, WrapperDescriptor))


class Interface(metaclass=MultiMeta):
    def __new__(cls, *args, **kwargs):
        raise _errors.err_depth(TypeError, "Interfaces cannot be instantiated.", depth=1)

    @classmethod
    def __check_obj__(cls, obj):
        """
        Simple hook to the builtin isinstance() function.
        """
        return NotImplemented

    @classmethod
    def __check_subclass__(cls, subclass):
        """
        Simple hook to the builtin issubclass() function.
        """
        return NotImplemented

    @classmethod
    def __instancehook__(cls, instance):
        return cls.__check_obj__(instance)

    @classmethod
    def __subclasshook__(cls, subclass):
        return cls.__check_subclass__(subclass)


class Buffer(Interface):
    """
    Interface representing objects that support the buffer protocol.
    isinstance(x, Buffer) returns whether x supports the buffer protocol.

    Subclass check is not supported as there is no way in python to know
    if a class implements the buffer protocol.
    """
    def __init_subclass__(cls, **kwargs):
        """
        Implement class X(t_instance)
        """
        raise _errors.err_depth(TypeError, "Cannot implement the buffer protocol in pure python.", depth=1)

    @classmethod
    def __check_obj__(cls, obj):
        """
        Check if an object supports the buffer protocol.
        """
        if ctypes.pythonapi.PyObject_CheckBuffer(ctypes.py_object(obj)):
            return True
        return NotImplemented


class SupportsIndex(Interface):
    @classmethod
    def __check_obj__(cls, obj):
        if _instance_has_method(obj, __INDEX__):
            return True
        return NotImplemented

    @classmethod
    def __check_subclass__(cls, subclass):
        if _class_has_method(subclass, __INDEX__):
            return True
        return NotImplemented

    def __index__(self) -> int: ...


class SupportsFloat(Interface):
    @classmethod
    def __check_obj__(cls, obj):
        if _instance_has_method(obj, __FLOAT__):
            return True
        return NotImplemented

    @classmethod
    def __check_subclass__(cls, subclass):
        if _class_has_method(subclass, __FLOAT__):
            return True
        return NotImplemented

    def __float__(self) -> float: ...


class SupportsBool(Interface):
    @classmethod
    def __check_obj__(cls, obj):
        if _instance_has_method(obj, __BOOL__):
            return True
        return NotImplemented

    @classmethod
    def __check_subclass__(cls, subclass):
        if _class_has_method(subclass, __BOOL__):
            return True
        return NotImplemented

    def __bool__(self) -> bool: ...

