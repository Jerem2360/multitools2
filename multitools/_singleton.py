"""
Basic implementation that mimics the behaviour of singletons.
"""

__DISPLAY_NAME__ = '__display_name__'

import sys
import typing

from .errors import err_depth


class _SingletonMeta(type):
    def __new__(mcs, name, bases, np):

        cls = super().__new__(mcs, name, bases, np)
        cls._value = None
        cls.__display_name__ = np[__DISPLAY_NAME__] if __DISPLAY_NAME__ in np else 'Singleton'
        cls._inheritable = cls.__base__ is object
        cls._overrides = np
        return cls


class SingletonType(metaclass=_SingletonMeta):
    def __new__(cls, *args, **kwargs):
        if cls._value is None:
            cls._value = object.__new__(cls)
        return cls._value

    def __init_subclass__(cls, **kwargs):
        if not cls._inheritable:
            # noinspection PyTypeChecker
            raise err_depth(TypeError, "", depth=1)

    def __reduce__(self):
        return (
            singleton,
            (type(self).__name__, type(self).__module__, type(self)._overrides),
        )

    def __eq__(self, other):
        return isinstance(other, type(self))

    def __repr__(self):
        return self.__display_name__

    def super(self):
        return super(type(self), self)


def singleton(name, modname, overrides={}) -> SingletonType:
    """
    Construct a basic custom singleton with its own type object, named <name>_t.
    'name' is used as the return value of __repr__ and __eq__ returns True only for
    the singleton itself. __new__ will always return the same object, meaning
    the 'is' comparison will return True only for the singleton itself.
    To customize behaviour, decorate a class with @Singleton. It will be
    replaced with the singleton object itself.
    Note that modname must represent an existing and already imported module.
    """
    t = _SingletonMeta(name + '_t', (SingletonType,), {__DISPLAY_NAME__: name, '__module__': modname})
    for k, v in overrides.items():
        setattr(t, k, v)

    # update the module with the singleton's type so pickle can handle it correctly:
    setattr(sys.modules[modname], name + '_t', t)
    return t()


_T = typing.TypeVar('_T')


def Singleton(cls: type[_T]) -> _T:
    """
    Decorator to convert a class into a singleton object.
    Methods can be overridden in the decorated class' body,
    but self.super() or super(type(self), self) must be used
    instead of super().
    """
    name = cls.__name__
    modname = cls.__module__
    overrides = dict(cls.__dict__).copy()
    del overrides['__module__'], overrides['__dict__'], overrides['__weakref__'], overrides['__doc__']
    return singleton(name, modname, overrides=overrides)

