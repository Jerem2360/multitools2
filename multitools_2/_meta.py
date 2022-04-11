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

