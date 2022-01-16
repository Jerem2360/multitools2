from .._meta import *
from .. import system
from .._ref import *
import ctypes as _ctypes


class ExternalFunction(metaclass=MultiMeta):
    _valid_types = {
        int, float, bool, str, None, bytes
    }
    def __init__(self, funcptr, argtypes, restype):
        self._handle = funcptr
        self._handle.argtypes = argtypes
        self._handle.restype = restype

    def _manage_type(self, tp):



class Library(metaclass=MultiMeta):
    def __init__(self, library: system.Library):
        self._handle = library

    def __getattr__(self, item):


    @staticmethod
    def load(library, flags=0):
        return Library(system.Library.load(library, flags=flags))


