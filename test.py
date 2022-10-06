import pickle
import copyreg

from multitools.interop import *
from multitools._meta import MultiMeta

_Pickler = pickle._Pickler
_Unpickler = pickle._Unpickler


class C_Meta(MultiMeta):
    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls.super_name = 'SUPER_' + args[0]

    def __getstate__(cls):
        print('getstate')
        return {'sname': cls.super_name}

    def __setstate__(cls, state):
        print('setstate')
        cls.super_name = state['sname']


class C(metaclass=C_Meta): ...


a = pickle.dumps(C)
_C = pickle.loads(a)

print(_C, a)
print(_C.super_name)

