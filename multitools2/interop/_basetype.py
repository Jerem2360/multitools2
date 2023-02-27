from .._internal.meta import *


class CType(MultiMeta):
    def __new__(mcs, name, bases, np, **kwargs):

        cls = super().__new__(mcs, name, bases, np, **kwargs)
        return cls

    def __alloc__(cls, data):
        return
