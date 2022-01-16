from .._meta import *
import _ctypes


class Library(metaclass=MultiMeta):
    def __init__(self, handle):
        self._handle = handle

    def __getattr__(self, item):
        function = self.find_reference(item)
        return function

    def find_reference(self, ref, flags=0):
        class FuncWrapper(_ctypes.CFuncPtr):
            _flags_ = flags
        function = FuncWrapper((ref, self))
        return function

    @staticmethod
    def Load(name, flags=0):
        return Library(_ctypes.LoadLibrary(name, flags))

