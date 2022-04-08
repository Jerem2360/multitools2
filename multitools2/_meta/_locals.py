from dataclasses import dataclass

from ._const import *


def has_dec(value, dec):
    """
    Return whether the provided field has been decorated in the specified way.
    """
    try:
        return getattr(value, dec)
    except AttributeError:
        return False


def give_dec(value, dec):
    """
    Decorate the provided field in the provided way and return it.
    """
    setattr(value, dec, True)
    return value


def is_function(obj):
    """
    Return whether an object is a function / method or not.
    """
    func_t = type(lambda: None)
    builtin_func_t = type(print)
    return isinstance(obj, (func_t, builtin_func_t, staticmethod, classmethod))


#----- Avoid MultiMeta as metaclass for types that MultiMeta uses, it could create infinite recursion -----#

class MultiType(type):
    """
    The metaclass for all multitools types.
    """
    def __repr__(cls):
        return f"<multitools class '{cls.__name__}'>"

    def __getitem__(cls, item):
        if hasattr(cls, '__class_getitem__'):
            return cls.__class_getitem__(item)
        return cls


class Field(metaclass=MultiType):
    """
    Fields are wrappers for attributes of MultiMeta classes.
    """
    def __init__(self, value):
        super().__setattr__(SEC_VALUE, value)

    def value(self, instance, owner):
        """
        Return the value contained by the Field, on which instance and owner
        have been applied.
        """
        val = self.raw
        if hasattr(val, '__get__'):
            return val.__get__(instance, owner)
        return val

    is_function = property(lambda self: is_function(self.raw))
    """Return whether this Field is a function or not."""
    raw = property(lambda self: super().__getattribute__('__dict__')[SEC_VALUE])
    """Return the value contained into the field, without anything applied onto it."""


class Data(metaclass=MultiType):
    """
    The __data__ attribute of MultiMeta classes.
    """
    def __init__(self,
                 name: str,
                 bases: tuple[type],
                 static: dict[str, Field],
                 instance: dict[str, Field],
                 mro: list[type],
                 flags: int):
        self.name: str = name
        self.bases: tuple[type] = bases
        self.static: dict[str, Field] = static
        self.instance: dict[str, Field] = instance
        self.mro: list[type] = mro
        self.flags: int = flags


def assure_field(value):
    """
    Convert value to a field if necessary. The result is guaranteed to be a
    field object.
    """
    return value if isinstance(value, Field) else Field(value)
