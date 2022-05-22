from ._local import *
from ._const import *


@customPath(GLOBAL_NAME)
class MultiMeta(type):
    def __new__(mcs, *args, **kwargs):
        cls = super().__new__(mcs, *args, **kwargs)
        cls_mod_old = cls.__module__.split('.')
        if len(cls_mod_old) <= 2:
            return cls
        sub = cls_mod_old[1]
        cls.__module__ = f"{GLOBAL_NAME}.{sub}"
        return cls

    @staticmethod
    def copy(instance, *newargs, **newkwargs):
        """
        Create a copy of instance in memory and return it.
        """
        copy = type(instance).__new__(type(instance), *newargs, **newkwargs)
        copy.__dict__ = instance.__dict__.copy()
        return copy

    @staticmethod
    def get_info(obj, name, default=None):
        try:
            return getattr(obj, f"#{name}")
        except AttributeError as e:
            if default is None:
                raise AttributeError(*e.args) from None
            return default

    @staticmethod
    def set_info(obj, name, value):
        setattr(obj, f"#{name}", value)
        return obj

