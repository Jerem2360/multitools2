from importlib.machinery import ModuleSpec
from typing import Any


from ._library import *
from .._const import *
from .._typing import type_check as _tp_check


__all__ = [
    "DllImport",
]


class _Spec(ModuleSpec):
    def __init__(self, name: Any, loader: Any, *, origin=None, loader_state=None,
                 is_package=None):
        super().__init__(name, loader, origin=origin, loader_state=loader_state, is_package=is_package)


class DllParentSpec(_Spec):
    def __init__(self):
        super().__init__(DLL_PARENT_MODULE_NAME, None, is_package=True)


class DllLoader:
    def load_module(self, name):
        mod = Library.load(name + DLL_EXTENSION, flags=1)
        mod.__file__ = name + DLL_EXTENSION
        sys.modules[name] = mod
        return mod


class DllSpec(_Spec):
    def __init__(self, name):
        super().__init__(name, DllLoader(), origin=name+DLL_EXTENSION, is_package=False)


class DllFinder:
    @classmethod
    def find_spec(cls, name, path, target=None):
        if name == DLLIMPORT_FROM_NAME:
            return DllParentSpec()

        if ('.' in name) and (len(name.split('.')) == 2) and (name.split('.')[0] == DLL_PARENT_MODULE_NAME):
            return DllSpec(name.split('.')[1])
        return None


# noinspection PyTypeChecker
sys.meta_path.insert(2, DllFinder)


def DllImport(name, funcflags=0, libflags=0):
    _tp_check((name, funcflags, libflags), str, int, int)

    def _wrap(func):
        if not hasattr(func, '__annotations__') or isinstance(func, type) or not callable(func) or not hasattr(func, '__name__'):
            raise TypeError(f"Expected decorated object of type 'function', got '{type(func).__name__}' instead.")

        annot = func.__annotations__
        restype = None
        if 'return' in annot:
            restype = annot['return']
            del annot['return']

        argtypes = []
        for key, value in annot.items():
            argtypes.append(value)

        return Library.load(name, flags=libflags).reference(func.__name__, argtypes=tuple(argtypes), restype=restype, flags=funcflags)

    return _wrap

