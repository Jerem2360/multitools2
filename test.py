import builtins
import ctypes
import sys
from importlib.machinery import ModuleSpec
import modulefinder
import nt


std_import = builtins.__import__
DLL_IMPORTER_NAME = '<dll file importer>'


class DllModule(type(ctypes)):
    def __init__(self, name):
        super().__init__(name)
        try:
            self.__dll__ = ctypes.CDLL(name)
        except FileNotFoundError:
            raise ModuleNotFoundError(name=name, path=f"{name}.dll")

    def __getattr__(self, item):
        try:
            return super().__getattribute__(item)
        except:
            return getattr(super().__getattribute__('__dll__'), item)


class DllParentSpec(ModuleSpec):
    def __init__(self):
        super().__init__(DLL_IMPORTER_NAME, None, origin=None, is_package=True)


class DllLoader:
    def __init__(self, name):
        self._dll = name

    def load_module(self, *args, **kwargs):
        mod = DllModule(self._dll)
        mod.__file__ = self._dll + '.dll'
        sys.modules[self._dll] = mod
        return mod


class DllSpec(ModuleSpec):
    def __init__(self, name):
        super().__init__(name, DllLoader(name), origin=f"{name}.dll", is_package=False)


class DllFinder:
    @classmethod
    def find_spec(cls, name, path, target=None):
        print(name, path, target)
        if name == 'dll':
            return DllParentSpec()

        if ('.' in name) and (len(name.split('.')) == 2) and (name.split('.')[0] == DLL_IMPORTER_NAME):
            # print(f"importing dll {name.split('.')[1]}")
            return DllSpec(name.split('.')[1])


sys.meta_path.insert(0, DllFinder)


from dll import user32

