"""
Meta path importers for the purpose of this library.
"""


from importlib import util as _util
import sys

from .._typeshed import *
from . import _import_data


__SPEC__ = '__spec__'
__FINALIZE__ = '__finalize__'


class _ImportMeta(type):
    def __init__(cls, *args, **kwargs):
        """
        Initialize a new importer class.
        It will be enabled by default.
        """
        super().__init__(*args, **kwargs)
        if cls.__base__ != object:
            cls.__meta_position__ = _import_data.__importer_count__
            _import_data.__importer_count__ += 1
            # noinspection PyTypeChecker
            sys.meta_path.insert(cls.__meta_position__, cls)

    def disable(cls):
        """
        Disable a custom importer.
        """
        if cls.__base__ != object:
            # noinspection PyTypeChecker
            sys.meta_path.pop(sys.meta_path.index(cls))
            _import_data.__disabled__ += 1

    def enable(cls):
        """
        Enable a custom importer.
        """
        if cls.__base__ != object:
            pos = cls.__meta_position__ - _import_data.__disabled__ if _import_data.__disabled__ <= cls.__meta_position__ else 0
            # noinspection PyTypeChecker
            sys.meta_path.insert(pos, cls)
            _import_data.__disabled__ -= 1
            if _import_data.__disabled__ < 0:
                _import_data.__disabled__ = 0


class _Importer(metaclass=_ImportMeta):
    @classmethod
    def find_spec(cls, name, path, target=None): ...
    @classmethod
    def exec_module(cls, module): ...
    @classmethod
    def create_module(cls, spec): ...


class _MultiImporter(_Importer):
    @classmethod
    def find_spec(cls, name, path, target=None):
        _GLOBAL_NAME = __package__.removeprefix('._startup')

        path_nodes = name.split('.')
        if not (len(path_nodes) == 2) or path_nodes[1].startswith('_') or (path_nodes[0] != _GLOBAL_NAME):
            return None

        sys.audit(f"{_GLOBAL_NAME}._MultiImporter.find_spec", name, path, target)
        if (path_nodes[1] in _import_data.__import_hooks__) and callable(_import_data.__import_hooks__[path_nodes[1]]):

            cls.disable()
            module = _import_data.__import_hooks__[path_nodes[1]](name, path, target=target)
            cls.enable()

            if module is None:
                return None
            if not hasattr(module, __SPEC__):
                raise AttributeError(f"import hook '{path_nodes[1]}': missing __spec__ attribute for returned module.")
            spec = module.__spec__

        else:
            cls.disable()
            spec = _util.find_spec(name, path)
            cls.enable()
            if spec is None:
                return None

        spec.__loader__ = cls
        return spec

    @classmethod
    def create_module(cls, spec):
        module = Module(spec.name)
        module.__spec__ = spec
        return module

    @classmethod
    def exec_module(cls, module):
        if module.__file__ is None:
            return module
        file = open(module.__file__, 'r+')
        code = file.read()
        file.close()
        exec(compile(code, module.__file__, 'exec'), module.__dict__)

        if hasattr(module, __FINALIZE__):
            _import_data.__finalizers__[module.__name__ + '.__finalize__'] = module.__finalize__
            del module.__finalize__

        return module


class _ModuleSpec:
    def __init__(self, name, loader, *, origin=None, loader_state=None, is_package=None):
        self.name = name
        self.loader = loader
        self.origin = origin
        self.cached = None
        self.submodule_search_locations = name if is_package else None
        self.parent = name if is_package else ""
        self.loader_state = loader_state
        self.has_location = origin is not None

