from importlib import util as _u

from ._const import *


__all__ = []
__on_exit__ = {}


def _add_on_exit(source, func):
    __on_exit__[source] = func


class _MultitoolsSubModuleFinder:
    @classmethod
    def find_spec(cls, name, path, target=None):

        list_path = name.split(".")

        if not (1 < len(list_path) < 3) or list_path[1].startswith('_') or (list_path[0] != GLOBAL_NAME):
            return None
        if list_path[1] == "dll":  # known special case for multitools.dll
            return None

        sys.meta_path.pop(0)  # to avoid recursion we remove temporarily our pathfinder from meta path.
        mod_spec = _u.find_spec(name, path)
        if mod_spec is None:
            return None

        mod = mod_spec.loader.load_module(name)
        if hasattr(mod, '__finalize__') and callable(mod.__finalize__):
            _add_on_exit(name, mod.__finalize__)
            del mod.__finalize__

        sys.meta_path.insert(0, _MultitoolsSubModuleFinder)  # restore our pathfinder.
        return mod_spec


import sys


sys.meta_path.insert(0, _MultitoolsSubModuleFinder)


import threading

# _shutdown() borrowed from the threading module:
# noinspection PyProtectedMember
_buffer = threading._shutdown


def _shutdown(*args, **kwargs):
    import traceback
    exc_info = sys.exc_info()

    _buffer(*args, **kwargs)  # execute threading's initial _shutdown()

    for source, callback in __on_exit__.items():
        try:
            callback(*exc_info)
        except:
            sys.stderr.write(f"Failed to finalize {GLOBAL_NAME}.{source}. Traceback:\n")
            traceback.print_exc()
            break


threading._shutdown = _shutdown

