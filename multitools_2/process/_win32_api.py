import ctypes
import sys
from ctypes import wintypes
import _ctypes

LPPROC_THREAD_ATTRIBUTE_LIST = ctypes.c_void_p
EXTENDED_STARTUPINFO_PRESENT = 0x00080000

_encoding = sys.getdefaultencoding()


def _int_to_handle(obj):
    return ctypes.cast(ctypes.c_uint(obj), wintypes.HANDLE)


def _set_winerr():
    ctypes.pythonapi.PyErr_SetFromWindowsErr(wintypes.DWORD(_ctypes.get_last_error()))


class STARTUPINFOA(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPSTR),
        ("lpDesktop", wintypes.LPSTR),
        ("lpTitle", wintypes.LPSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", wintypes.LPBYTE),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class STARTUPINFOEXA(ctypes.Structure):
    _fields_ = [
        ("StartupInfo", STARTUPINFOA),
        ("lpAttributeList", LPPROC_THREAD_ATTRIBUTE_LIST),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.StartupInfo = STARTUPINFOA()


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


_kernel32 = ctypes.WinDLL("kernel32.dll")
_kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
_kernel32.CloseHandle.restype = wintypes.BOOL
ctypes.pythonapi.PyErr_SetFromWindowsErr.argtypes = (wintypes.DWORD,)
ctypes.pythonapi.PyErr_SetFromWindowsErr.restype = None
_kernel32.CreateProcessA.argtypes = (
    wintypes.LPCSTR, wintypes.LPSTR, ctypes.c_void_p, ctypes.c_void_p, wintypes.BOOL, wintypes.DWORD,
    wintypes.LPVOID, wintypes.LPCSTR, ctypes.POINTER(STARTUPINFOEXA), ctypes.POINTER(PROCESS_INFORMATION)
)
_kernel32.CreateProcessA.restype = wintypes.BOOL
ctypes.pythonapi.PyEval_SaveThread.argtypes = ()
ctypes.pythonapi.PyEval_SaveThread.restype = ctypes.c_void_p
ctypes.pythonapi.PyEval_RestoreThread.argtypes = (ctypes.c_void_p,)
ctypes.pythonapi.PyEval_RestoreThread.restype = None


def _begin_allow_threads():
    return ctypes.pythonapi.PyEval_SaveThread().value

def _end_allow_threads(_tstate):
    ctypes.pythonapi.PyEval_RestoreThread(ctypes.cast(_tstate, ctypes.c_void_p))


class Handle(int):
    def __new__(cls, *args, **kwargs):
        self = cls.__new__(cls, *args, **kwargs)
        self._closed = False
        return self

    # noinspection PyAttributeOutsideInit
    def close(self):
        if not self._closed:
            self._closed = True
            if not _kernel32.CloseHandle(_int_to_handle(self)).value:
                _set_winerr()

    def __del__(self):
        try:
            self.close()
        except WindowsError:
            pass


def CreateProcess(lpCommandLine, bInheritHandles, dwCreationFlags, lpEnvironment,
                  lpCurrentDirectory, lpStartupInfo):
    cmdline = wintypes.LPSTR(bytes(lpCommandLine, encoding=_encoding))
    inherit_handles = wintypes.BOOL(bInheritHandles)
    creation_flags = wintypes.DWORD(dwCreationFlags | EXTENDED_STARTUPINFO_PRESENT)

    environ_list = []

    for key, value in lpEnvironment.items():
        environ_list.append(key + '=' + value)

    environ = (ctypes.c_wchar_p * len(environ_list))(*environ_list)
    curdir = wintypes.LPCSTR(bytes(lpCurrentDirectory, encoding=_encoding))
    startupinfo = STARTUPINFOEXA()
    startupinfo.StartupInfo.dwFlags = wintypes.DWORD(lpStartupInfo.dwFlags)
    startupinfo.StartupInfo.wShowWindow = wintypes.WORD(lpStartupInfo.wShowWindow)
    startupinfo.StartupInfo.hStdInput = wintypes.HANDLE(lpStartupInfo.hStdInput)
    startupinfo.StartupInfo.hStdOutput = wintypes.HANDLE(lpStartupInfo.hStdOutput)
    startupinfo.StartupInfo.hStdError = wintypes.HANDLE(lpStartupInfo.hStdError)
    process_info = PROCESS_INFORMATION()

    _t = _begin_allow_threads()
    res = _kernel32.CreateProcessA(
        None,
        cmdline,
        None, None,
        inherit_handles,
        creation_flags,
        environ,
        curdir,
        startupinfo,
        ctypes.pointer(process_info),
    )
    _end_allow_threads(_t)
    if not res.value:
        _set_winerr()

    return Handle(process_info.hProcess.value), Handle(process_info.hThread.value), \
        process_info.dwProcessId.value, process_info.dwThreadId.value
