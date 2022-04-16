import ctypes
import _ctypes


def dllimport(lib):
    def _inner(func):
        library = ctypes.CDLL(lib)
        function = library[func.__name__]

        if 'return' in func.__annotations__:
            function.restype = func.__annotations__['return']
            del func.__annotations__['return']
        else:
            function.restype = None

        argtypes = [func.__annotations__[argtp] for argtp in func.__annotations__]
        function.argtypes = tuple(argtypes)
        return function
    return _inner

