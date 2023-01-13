import sys



__all__ = [
    '__NAME__',
    '__DEBUG__',
    '__ROOT__',
    '__trace_refs__',
    'IS_SYSTEM_x64',
    'MS_WIN32',
    'MS_WIN64',
    'ANDROID',
    '__APPLE__',
]


__NAME__ = ''  # real value of type str assigned later at runtime
__DEBUG__ = True
__ROOT__ = ...  # real value of type module assigned later at runtime

# same as the Py_TRACE_REFS macro of the C api: https://github.com/python/cpython/blob/main/Misc/SpecialBuilds.txt
__trace_refs__ = hasattr(sys, 'getobjects')

IS_SYSTEM_x64 = sys.maxsize > 2 ** 31 - 1  # if the host machine has a 64-bit system

MS_WIN32 = sys.platform == "win32"  # if the host is Windows machine
MS_WIN64 = MS_WIN32 and IS_SYSTEM_x64  # if the host is a Windows x64 machine
ANDROID = hasattr(sys, 'getandroidapilevel')

__APPLE__ = sys.platform == "darwin"  # if the host is a MacOSx machine

