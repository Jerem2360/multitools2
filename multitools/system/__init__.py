from . import _external
from ._external import Library
import sys
from . import _gl

__all__ = [
    "Library",
    "external",
    "SecretCtypes",
    "is_an_admin",
    "runas_admin",
]


def external(library: str, function: str, flags=0) -> _external.CFuncPtr:
    """
    Load a function from an external library into memory.
    Returns a _ctypes.CFuncPtr wrapper to the function.
    """
    lib = Library.load(library, flags=flags)
    func = lib.getfunc(function, flags=flags)
    return func


class SecretCtypes:
    """
    Namespace containing some unreachable types of the
    ctypes module.
    """
    CFuncPtr = _external.CFuncPtr
    PyCFuncPtrType = _external.PyCFuncPtrType
    CData = _external.CData


def is_an_admin() -> bool:
    """
    Return whether the current process is running
    as administrator on the machine.
    """
    is_admin = external("C:/Windows/System32/shell32.dll", "IsUserAnAdmin")
    is_admin.restype = int
    is_admin.argtypes = ()
    return is_admin() != 0


def runas_admin(file: str, args: str, flags: int = 1) -> int:
    """
    Run a program as administrator, invoking the UAC (or User Account Control)
    to ask for permissions.
    Return exit code.

    If exit code is smaller or equal to 32, an error occurred.
    """
    shell_execute = external("C:/Windows/System32/shell32.dll", "ShellExecuteW")
    shell_execute.restype = int
    code = shell_execute(None, "runas", file, args, None, flags)
    return code


def get_last_error():
    gle = external("C:/Windows/System32/kernel32.dll", "GetLastError")
    gle.restype = int
    gle.argtypes = ()
    return gle()

