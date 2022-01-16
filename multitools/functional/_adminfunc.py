from .. import system
from .._meta import *
import pickle
import sys
import types


def needs_admin(func):
    return FuncNeedsAdmin(func.__code__, globals(), name=func.__name__)


class FuncNeedsAdmin(types.FunctionType, metaclass=MultiMeta):
    def __init__(self, code, globals_, name=None, argdefs=None, closure=None):
        self._true_code = pickle.dumps(code)
        self._true_gl = pickle.dumps(globals_)
        self._exec_code = f"import pickle, sys, types; " \
                          f"sys.argv.pop(0);" \
                          f"code = pickle.loads({repr(self._true_code)});" \
                          f"gl = pickle.loads({repr(self._true_gl)})" \
                          f"function = types.FunctionType(code, globals, name={repr(name)}, argdefs={repr(argdefs)}, closure={repr(closure)});"
        # noinspection PyArgumentList
        super().__init__(code, globals_, name=name, argdefs=argdefs, closure=closure)

    def __call__(self, *args, **kwargs):
        argv = sys.argv
        argv.pop(0)
        command_args = f"-c \"{self._exec_code}\" {' '.join(argv)}"
        print(f"{sys.executable} {command_args}")


class AdminFunc(metaclass=MultiMeta):
    def __init__(self, func):
        fn = pickle.dumps(func)
        self._funcstr = "import pickle;" \
                        "import sys;" \
                        "sys.argv.pop(0);" \
                        f"function = pickle.loads({repr(fn)});" \
                        f"del sys;"
        del fn

    def __call__(self, *args, **kwargs):
        args_p = pickle.dumps(args)
        kwargs_p = pickle.dumps(kwargs)
        callfunc = f"function(*pickle.loads({repr(args_p)}), **pickle.loads({repr(kwargs_p)}))"
        gl = pickle.dumps(globals())

        code = f"exec(\"{self._funcstr + callfunc}\", pickle.loads({repr(gl)}), {repr(dict())})"
        system.runas_admin(sys.executable, f"-c \"{code}\" {' '.join(sys.argv)}")

