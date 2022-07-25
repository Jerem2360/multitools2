import _thread

from ._local import *
from ._const import *


@customPath(GLOBAL_NAME)
class MultiMeta(type):
    def __new__(mcs, *args, **kwargs):
        cls = super().__new__(mcs, *args, **kwargs)
        cls_mod_old = cls.__module__.split('.')
        if len(cls_mod_old) <= 2:
            return cls
        cls.__real_module__ = cls.__module__
        sub = cls_mod_old[1]
        cls.__module__ = f"{GLOBAL_NAME}.{sub}"
        return cls

    def __getitem__(cls, item):
        pass

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
        lock = getattr(obj, f"#{name}:lock")
        lock.acquire(blocking=True)
        try:
            return getattr(obj, f"#{name}")
        except AttributeError as e:
            if default is None:
                raise AttributeError(*e.args) from None
            return default
        finally:
            lock.release()

    @staticmethod
    def set_info(obj, name, value):
        if not hasattr(obj, f"#{name}:lock"):
            setattr(obj, f"#{name}:lock", _thread.allocate_lock())

        lock = getattr(obj, f"#{name}:lock")
        lock.acquire(blocking=True)
        setattr(obj, f"#{name}", value)
        lock.release()
        return obj

    @staticmethod
    def has_info(obj, name):
        return f'#{name}' in object.__dir__(obj)

