import _thread
import _winapi
import errno as _errno
import os
import random

import _ctypes as _ct
import ctypes as _ctypes
import sys
from ctypes import wintypes as _wt
import contextlib


from ._errors import _NoPath, ATTRIB_ERR_STR
from ._builtindefs import Method
from ._const import *
from . import _helpers
from . import _typing

# print(locale.setlocale(locale.LC_NUMERIC, 'en_US'))

_kernel32 = _ctypes.WinDLL('kernel32.dll')


SW_HIDE = 0
STARTF_USESTDHANDLES = 256
STARTF_USESHOWWINDOW = 1
CREATE_NEW_CONSOLE = 16

STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE = -12
INVALID_HANDLE_VALUE = -1

FORMAT_MESSAGE_ALLOCATE_BUFFER = 0x00000100
FORMAT_MESSAGE_FROM_SYSTEM = 0x00001000
FORMAT_MESSAGE_IGNORE_INSERTS = 0x00000200

PAGE_READWRITE = 4
FILE_MAP_READ = 4

LANG_NEUTRAL = 0x00
SUBLANG_NEUTRAL = 0x00
SUBLANG_DEFAULT = 0x01

LANG_ENGLISH = 0x09
SUBLANG_ENGLISH_US = 0x01
def MAKELANGID(primary, sublang):
    return (primary & 0xFF) | (sublang & 0xFF) << 16

LCID_ENGLISH = MAKELANGID(LANG_ENGLISH, SUBLANG_ENGLISH_US)
LCID_DEFAULT = MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT)
LCID_NEUTRAL = MAKELANGID(LANG_NEUTRAL, SUBLANG_NEUTRAL)
assert LCID_NEUTRAL == 0


PROCESS_ALL_ACCESS = _winapi.PROCESS_ALL_ACCESS
PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_DUP_HANDLE = 0x0040
PROCESS_CREATE_THREAD = 0x0002
SYNCHRONIZE = 0x00100000

THREAD_SUSPEND_RESUME = 0x0002
THREAD_QUERY_INFORMATION = 0x0040

TH32CS_SNAPTHREAD = 0x00000004


ERROR_ACCESS_DENIED = 5
ERROR_WRITE_PROTECT = 19
ERROR_SHARING_VIOLATION = 32
ERROR_INVALID_PARAMETER = 87
ERROR_ALREADY_EXISTS = 183


SHM_SAFE_NAME_LENGTH = 14
SHM_NAME_PREFIX = 'wnsm_'


INFINITE = 0xFFFFFFFF


WAIT_ABANDONED = 0x00000080
WAIT_IO_COMPLETION = 0x000000C0
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102


STILL_ACTIVE = 259


def _FormatMessageSystem(_id, langid=LCID_ENGLISH):
    sys_flag = FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS

    bufptr = _wt.LPWSTR()

    chars = _kernel32.FormatMessageW(sys_flag, None, _id, langid, _ctypes.byref(bufptr), 0, None)
    if chars == 0:
        chars = _kernel32.FormatMessageW(sys_flag, None, _id, LCID_NEUTRAL, _ctypes.byref(bufptr), 0, None)
        if chars == 0:
            # XXX: You probably want to call GetLastError() here
            return _ctypes.GetLastError()

    val = bufptr.value[:chars]

    _ctypes.windll.kernel32.LocalFree(bufptr)

    return val


def format_winerror(winerror):
    """
    Format a Windows error message.
    """
    res = _FormatMessageSystem(winerror)
    if isinstance(res, int):
        raise OSError(f"Failed to format error {winerror}. Reason: {res}")
    return res


def error_from_winerror(winerror):
    """
    Return an OSError containing the given Windows error code formatted.
    """
    res = _FormatMessageSystem(winerror)
    if isinstance(res, int):  # error
        return res

    return WindowsError(0, res, None, winerror)


def winerror(code):
    """
    Create and return a python error that is adapted to the given error.
    Error codes over 200 always give OSError.
    """
    etype = WindowsError
    if code in _winerr_types:
        etype = _winerr_types[code]

    text = _FormatMessageSystem(code)
    if isinstance(text, int):
        raise OSError(f"Failed to format error {code}. Reason: {text}")

    if etype == WindowsError:
        return WindowsError(0, text, None, code)

    err = etype(f"[WinErr {code}] {text}")
    err.winerror = code
    err.strerror = text
    return err


def winerror_from_exception(exception):
    """
    Format a python exception accordingly to the given OSError.
    """
    etype = _winerr_types[exception.winerror] if exception.winerror in _winerr_types else OSError
    return etype(exception.strerror)


def winerror_last():
    err = sys.exc_info()[1]
    if not isinstance(err, (OSError, WindowsError)):
        return err
    etype = _winerr_types[err.winerror] if err.winerror in _winerr_types else OSError
    new_err = etype(err.strerror)
    new_err.__cause__ = err.__cause__
    new_err.__traceback__ = err.__traceback__
    new_err.__context__ = err.__context__
    return new_err


def FIELD_OFFSET(t, f):
    # return ctypes.addressof(getattr(ctypes.cast(0, ctypes.POINTER(t)), f))
    inst = t()
    field = getattr(inst, f)
    if isinstance(field, int):
        field = _ctypes.c_ulonglong(field) if field >= 0 else _ctypes.c_longlong(field)
    print(t, f)
    print(type(field))
    return _ctypes.addressof(field) - _ctypes.addressof(inst)


class Handle(int):
    """
    Simple class representing a windows handle.
    """
    __instances = {}

    # borrowed from subprocess module
    def __init__(self, *args, **kwargs):
        """
        Create and return a new Handle object, given its integer value.
        """
        super().__init__()
        self._closed = False
        if int(self) in Handle.__instances:  # increment refcount if we already exist
            Handle.__instances[int(self)] += 1
        else:  # add ourselves to the list if we don't already exist.
            Handle.__instances[int(self)] = 1

    def close(self):
        """
        Close the underlying handle value of this instance. If multiple Handle objects
        that reference this value are still alive, the handle integer value is not closed itself.
        """
        if not self._closed:
            Handle.__instances[int(self)] -= 1  # decrement refcount
            if Handle.__instances[int(self)] <= 0:  # if no more refs are left, close the handle value.
                try:
                    _winapi.CloseHandle(self)
                except OSError:
                    pass
                del Handle.__instances[int(self)]
            self._closed = True  # even if the handle value itself is not closed, this instance is considered closed.

    def detach(self):
        """
        Detach this instance from its value, closing the handle on the way.
        Return the actual handle's value.
        """
        self.check_open()
        if not self._closed:
            Handle.__instances[int(self)] -= 1  # decrement refcount
            if Handle.__instances[int(self)] <= 0:  # if no more refs are left, close the handle value.
                try:
                    _winapi.CloseHandle(self)
                except OSError:
                    pass
                del Handle.__instances[int(self)]

            self._closed = True
            return int(self)
        raise ValueError("already closed")

    def duplicate(self, inheritable=False):
        """
        Duplicate a handle, with the ability to make the new one inheritable.
        """
        self.check_open()
        return Handle(_winapi.DuplicateHandle(
            _winapi.GetCurrentProcess(),
            int(self),
            _winapi.GetCurrentProcess(),
            0,
            inheritable,
            _winapi.DUPLICATE_SAME_ACCESS
        ))

    def check_open(self):
        """
        Raise an exception if the handle is closed.
        """
        if self._closed:
            raise ValueError('Closed handle.')

    def __reduce__(self):
        """
        Helper for pickle.
        """
        return (self.__class__,
                (int(self),)
                )

    def __repr__(self):
        """
        Implement repr(self)
        """
        return f"<handle {int(self)} at {hex(id(self))}>"

    def __del__(self):
        """
        Implement del self
        """
        try:
            self.close()
        except:
            pass

    @property
    def refcnt(self):
        """
        The number of alive Handle instances that refer to the same
        exact value as this instance, including self.
        Closed instances are not counted.
        """
        if int(self) in Handle.__instances:
            return Handle.__instances[int(self)]
        return 0

    closed = property(lambda self: self._closed)
    """Whether this instance is closed."""


class BetterStruct(_ctypes.Structure):
    _fields_ = ()
    def _get_type_of_field(self, name):
        for field in self._fields_:
            if field[0] == name:
                return field[1]
        raise AttributeError(ATTRIB_ERR_STR.format(self.__class__, name))

    def __getattribute__(self, item):
        val = super().__getattribute__(item)
        # print(type(val))

        if isinstance(val, Method) or item in ('__class__', '_fields_'):
            return val
        try:
            tp = self._get_type_of_field(item)
        except AttributeError:
            return val

        # print('getattr', item, 'type=' + type(val).__name__)
        if isinstance(val, int):
            # print('newtype:', tp.__name__)
            # noinspection PyProtectedMember
            if issubclass(tp, _ct._Pointer):
                return _ctypes.cast(val, tp)
            return tp(val)
        return val


class THREADENTRY32(BetterStruct):
    _fields_ = (
        ("dwSize", _wt.DWORD),
        ("cntUsage", _wt.DWORD),
        ("th32ThreadId", _wt.DWORD),
        ("th32OwnerProcessId", _wt.DWORD),
        ("tpBasePri", _ctypes.c_long),
        ("tpDeltaPri", _ctypes.c_long),
        ("dwFlags", _wt.DWORD)
    )
    def __init__(self,
                 dwSize=0,
                 cntUsage=0,
                 th32ThreadId=0,
                 th32OwnerProcessId=0,
                 tpBasePri=0,
                 tpDeltaPri=0,
                 dwFlags=0
                 ):
        super().__init__()
        self.dwSize = dwSize
        self.cntUsage = cntUsage
        self.th32ThreadId = th32ThreadId
        self.th32OwnerProcessId = th32OwnerProcessId
        self.tpBasePri = tpBasePri
        self.tpDeltaPri = tpDeltaPri
        self.dwFlags = dwFlags


# handles to the standard io streams:
raw_stdin = Handle(_winapi.GetStdHandle(STD_INPUT_HANDLE))

raw_stdout = Handle(_winapi.GetStdHandle(STD_OUTPUT_HANDLE))

raw_stderr = Handle(_winapi.GetStdHandle(STD_ERROR_HANDLE))


class StartupInfo:
    """
    Implementation of the STARTUPINFO structure in <Windows.h>
    """
    # borrowed from subprocess module
    def __init__(self, *, dwFlags=0, hStdInput=None, hStdOutput=None,
                 hStdError=None, wShowWindow=SW_HIDE, lpAttributeList=None):
        self.dwFlags = dwFlags
        self.hStdInput = hStdInput
        self.hStdOutput = hStdOutput
        self.hStdError = hStdError
        self.wShowWindow = wShowWindow
        self.lpAttributeList = lpAttributeList

    def copy(self):
        attr_list = self.lpAttributeList.copy() if self.lpAttributeList is not None else None

        return StartupInfo(dwFlags=self.dwFlags,
                           hStdInput=self.hStdInput,
                           hStdOutput=self.hStdOutput,
                           hStdError=self.hStdError,
                           wShowWindow=self.wShowWindow,
                           lpAttributeList=attr_list)

    def __getstate__(self):
        return {
            'flags': self.dwFlags,
            'hStdInput': self.hStdInput,
            'hStdOutput': self.hStdOutput,
            'hStdError': self.hStdError,
            'showWindow': self.wShowWindow,
            'attributeList': self.lpAttributeList,
        }

    def __setstate__(self, state):
        self.dwFlags = state['flags']
        self.hStdInput = state['hStdInput']
        self.hStdOutput = state['hStdOutput']
        self.hStdError = state['hStdError']
        self.wShowWindow = state['showWindow']
        self.lpAttributeList = state['attributeList']


def enum_proc_threads(pid):
    threads = []
    h = _kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    if h != INVALID_HANDLE_VALUE:
        te = THREADENTRY32()
        te.dwSize = _ctypes.sizeof(te)
        if _kernel32.Thread32First(h, _ctypes.byref(te)):
            while True:
                if not _kernel32.Thread32Next(h, _ctypes.byref(te)):
                    break
                """if (te.dwSize.value >= (FIELD_OFFSET(THREADENTRY32, 'th32OwnerProcessId') +
                                 _ctypes.sizeof(te.th32OwnerProcessId))) and (te.th32OwnerProcessId == pid):
                    threads.append(te.th32ThreadId)"""
                if te.th32OwnerProcessId.value == pid:
                    threads.append(te.th32ThreadId.value)
                # print(te.th32OwnerProcessId, _thread.get_native_id(), pid)
                te.dwSize = _ctypes.sizeof(te)
            _winapi.CloseHandle(h)

    return threads


def pipe():
    """
    Return a pair of handles to a newly created pipe.
    """
    pipe = _winapi.CreatePipe(None, 0)
    read = Handle(pipe[0])
    write = Handle(pipe[1])
    return read.duplicate(inheritable=True), write.duplicate(inheritable=True)


def read(descr, size):
    """
    Read up to size from a file descriptor or handle.
    """
    if isinstance(descr, Handle):
        descr.check_open()
        try:
            return _winapi.ReadFile(descr, size)[0]
        except WindowsError as e:
            match e.winerror:
                case 5:  # ERROR_ACCESS_DENIED
                    raise PermissionError(e.strerror) from None
                case 6:  # ERROR_INVALID_HANDLE
                    raise ValueError(e.strerror) from None
                case 14:  # ERROR_OUT_OF_MEMORY
                    raise MemoryError(e.strerror) from None
                case 30:  # ERROR_READ_FAULT
                    raise BlockingIOError(e.strerror) from None
                case 38:  # ERROR_HANDLE_EOF
                    raise EOFError(e.strerror) from None
                case 87:  # ERROR_INVALID_PARAMETER
                    raise ValueError(e.strerror) from None
                case 109:  # ERROR_BROKEN_PIPE
                    raise BrokenPipeError(e.strerror) from None
                case _:
                    raise e from None
    return os.read(descr, size)


def write(descr, data):
    """
    Write data to a file descriptor or handle.
    """
    if isinstance(descr, Handle):
        descr.check_open()
        try:
            return _winapi.WriteFile(descr, data)[0]
        except WindowsError as e:
            match e.winerror:
                case 5:  # ERROR_ACCESS_DENIED
                    raise PermissionError(e.strerror) from None
                case 6:  # ERROR_INVALID_HANDLE
                    raise ValueError(e.strerror) from None
                case 14:  # ERROR_OUT_OF_MEMORY
                    raise MemoryError(e.strerror) from None
                case 29:  # ERROR_WRITE_FAULT
                    raise BlockingIOError(e.strerror) from None
                case 87:  # ERROR_INVALID_PARAMETER
                    raise ValueError(e.strerror) from None
                case 109:  # ERROR_BROKEN_PIPE
                    raise BrokenPipeError(e.strerror) from None
                case _:
                    raise e from None
    return os.write(descr, data)


# noinspection PyShadowingBuiltins
def open(filename, mode='r'):
    """
    Open a file given filename. Return a valid file descriptor for it.
    Same values are allowed by 'mode' as for the builtin open() function.
    """
    imode = 0
    flags = 0
    read = 'r' in mode
    write = 'w' in mode
    append = 'a' in mode
    create = 'x' in mode
    binary = 'b' in mode
    text = '+' in mode

    error = (read * append) or (read * create) or (write * append) or (write * create) or (append * create) or (
                text * binary)
    if error:
        raise ValueError("Invalid value for parameter 'mode'.")

    if read and write:
        flags = os.O_RDWR
    elif read:
        flags = os.O_RDONLY
    elif write:
        flags = os.O_WRONLY
    elif append:
        flags = os.O_APPEND
    elif create:
        flags = os.O_CREAT

    if binary:
        imode = os.O_BINARY
    elif text:
        imode = os.O_TEXT

    return os.open(filename, flags, mode=imode)


def isatty(descr):
    if isinstance(descr, Handle):
        descr.check_open()
        return False
    return os.isatty(descr)


def close(descr):
    """
    Close a handle or a file descriptor.
    """
    if isinstance(descr, Handle):
        return descr.close()
    return os.close(descr)


def getpid():
    """
    Windows-specific implementation that returns
    the current process' pid.
    """
    pid = _kernel32.GetCurrentProcessId()
    if isinstance(pid, int):
        return pid
    return pid.value


def terminate(pid_or_handle):
    """
    Terminate a process, given its pid or an open handle to it.
    """
    if not isinstance(pid_or_handle, Handle):
        pid_or_handle = open_process(pid_or_handle)

    try:
        _winapi.TerminateProcess(pid_or_handle, -1)
    except OSError or WindowsError as e:
        if e.winerror == ERROR_INVALID_PARAMETER:
            raise winerror_last() from None
        return False
    return True


def kill(pid_or_handle):
    """
    On Windows, kill is the same as terminate.
    """
    return terminate(pid_or_handle)


def join(handle, timeout):
    """
    Wait for a process to terminate, given an open handle to it.
    """
    if timeout is None:
        timeout = INFINITE
    try:
        res = _winapi.WaitForSingleObject(handle, timeout)
    except OSError or WindowsError:
        raise winerror_last() from None

    if res == WAIT_TIMEOUT:
        raise TimeoutError('Timeout expired.')
    if res == WAIT_ABANDONED:
        return False
    return True


def exit_status(handle):
    """
    Return the exit status of a process, given an open handle to it.
    Return None if the process is still active.
    """
    try:
        res = _winapi.GetExitCodeProcess(handle)
    except OSError or WindowsError:
        raise winerror_last() from None

    if res == STILL_ACTIVE:
        return
    return res


def open_process(pid):
    """
    Open the process of given id and return an open handle to it.
    """
    # attempt multiple different access wrights in order to have the max possible:
    try:
        hProc = Handle(_winapi.OpenProcess(
            PROCESS_ALL_ACCESS,
            True,
            pid
        ))
    except OSError as e:
        if e.winerror == ERROR_INVALID_PARAMETER:
            raise ProcessLookupError(f'Process of id {pid} does not exist.') from None
        if e.winerror in (ERROR_ACCESS_DENIED, ERROR_WRITE_PROTECT, ERROR_SHARING_VIOLATION):
            try:
                hProc = Handle(_winapi.OpenProcess(
                    PROCESS_TERMINATE | PROCESS_QUERY_INFORMATION | PROCESS_DUP_HANDLE | PROCESS_CREATE_THREAD,
                    True,
                    pid
                ))
            except OSError as e1:
                if e.winerror in (ERROR_ACCESS_DENIED, ERROR_WRITE_PROTECT, ERROR_SHARING_VIOLATION):
                    try:
                        hProc = Handle(_winapi.OpenProcess(
                            PROCESS_TERMINATE | PROCESS_QUERY_INFORMATION | PROCESS_DUP_HANDLE,
                            True,
                            pid
                        ))
                    except OSError as e2:
                        raise winerror_from_exception(e2) from None
                else:
                    raise winerror_from_exception(e1) from None
        else:
            raise winerror_from_exception(e) from None

    return hProc


def _OpenThread(dwDesiredAccess, dwThreadId):
    res = _kernel32.OpenThread(
        _wt.DWORD(dwDesiredAccess),
        1,
        _wt.DWORD(dwThreadId)
    )
    if res == 0:
        ecode = _winapi.GetLastError()
        raise error_from_winerror(ecode)
    return res


def open_thread(tid):
    try:
        return Handle(_OpenThread(
            THREAD_SUSPEND_RESUME | THREAD_QUERY_INFORMATION | SYNCHRONIZE,
            tid
        ))
    except OSError:
        raise winerror_last()


def process(command, options):
    """
    Create a new process, and return an open handle to it.
    """
    p2c_pipe = options.get_option("p2c", None)
    c2p_pipe = options.get_option("c2p", None)
    err_pipe = options.get_option("err", None)
    exc_info_pipe = options.get_option("exc_info_pipe", pipe())
    startupinfo = options.get_option("startupinfo", StartupInfo())
    flags = options.get_option("flags", 0)
    env_vars = options.get_option("environ", {})
    curdir = options.get_option("curdir", "")
    close_fds = options.get_option("close_fds", False)
    create_console = options.get_option('create_console', False)

    caller_exc_info_pipe, called_exc_info_pipe = exc_info_pipe

    if curdir == "":
        curdir = None
    if env_vars == {}:
        env_vars = None

    use_std_handles = not create_console
    startupinfo = startupinfo.copy()
    attr_list = startupinfo.lpAttributeList

    have_handle_list = bool(attr_list and "handle_list" in attr_list and attr_list["handle_list"])
    if startupinfo.wShowWindow != 0:
        startupinfo.dwFlags |= STARTF_USESHOWWINDOW

    if use_std_handles:
        p2c_pipe = p2c_pipe if p2c_pipe is not None else pipe()
        c2p_pipe = c2p_pipe if c2p_pipe is not None else pipe()
        err_pipe = err_pipe if err_pipe is not None else pipe()

        proc_stdin_called, proc_stdin_caller = p2c_pipe
        proc_stdout_caller, proc_stdout_called = c2p_pipe
        proc_stderr_caller, proc_stderr_called = err_pipe

        startupinfo.dwFlags |= STARTF_USESTDHANDLES
        startupinfo.hStdInput = proc_stdin_called
        startupinfo.hStdOutput = proc_stdout_called
        startupinfo.hStdError = proc_stderr_called

    else:
        flags |= _win32.CREATE_NEW_CONSOLE

    if have_handle_list or (use_std_handles and close_fds):
        if attr_list is None:
            attr_list = startupinfo.lpAttributeList = {}
        handle_list = attr_list["handle_list"] = list(attr_list.get("handle_list", []))

        if use_std_handles:
            # noinspection PyUnboundLocalVariable
            handle_list += [int(proc_stdin_called), int(proc_stdout_called), int(proc_stderr_called), int(called_exc_info_pipe)]

    try:
        process_handle, thread_handle, process_id, thread_id = _winapi.CreateProcess(
            sys.executable,
            command,
            None, None,
            True,
            flags,
            env_vars,
            curdir,
            startupinfo
        )
    except WindowsError or OSError as e:
        raise winerror_from_exception(e)

    finally:
        with contextlib.ExitStack() as s:
            s.callback(_winapi.CloseHandle, called_exc_info_pipe)
            if use_std_handles:
                s.callback(_winapi.CloseHandle, proc_stdin_called)
                s.callback(_winapi.CloseHandle, proc_stdout_called)
                s.callback(_winapi.CloseHandle, proc_stderr_called)
                if close_fds:
                    # noinspection PyUnboundLocalVariable
                    s.callback(_winapi.CloseHandle, proc_stdin_caller)
                    # noinspection PyUnboundLocalVariable
                    s.callback(_winapi.CloseHandle, proc_stdout_caller)
                    # noinspection PyUnboundLocalVariable
                    s.callback(_winapi.CloseHandle, proc_stderr_caller)

    caller_pipes = (caller_exc_info_pipe,) if not use_std_handles else (
        proc_stdin_caller,
        proc_stdout_caller,
        proc_stderr_caller,
        caller_exc_info_pipe
    )

    proc_info = process_id, Handle(process_handle)
    thread_info = thread_id, Handle(thread_handle)
    return proc_info, thread_info, caller_pipes


def _CreateFileMapping(
        hFile,
        flProtect,
        dwMaximumSizeHigh,
        dwMaximumSizeLow,
        lpName
):
    hMap = _kernel32.CreateFileMappingA(
        _ctypes.c_void_p(hFile),
        0,
        _wt.DWORD(flProtect),
        _wt.DWORD(dwMaximumSizeHigh),
        _wt.DWORD(dwMaximumSizeLow),
        _wt.LPCSTR(bytes(lpName, encoding=DEFAULT_ENCODING))
    )
    if (_winapi.GetLastError() == ERROR_ALREADY_EXISTS) or (hMap == 0):
        raise error_from_winerror(_winapi.GetLastError())

    return hMap


def _OpenFileMapping(dwDesiredAccess, lpName: str):
    hMap = _kernel32.OpenFileMappingA(
        _wt.DWORD(dwDesiredAccess),
        1,
        _ctypes.c_char_p(bytes(lpName, encoding=DEFAULT_ENCODING))
    )
    if hMap == 0:
        raise error_from_winerror(_winapi.GetLastError())

    return hMap


def _MapViewOfFile(
        hFileMappingObject,
        dwDesiredAccess,
        dwFileOffsetHigh,
        dwFileOffsetLow,
        dwNumberOfBytesToMap
):
    pBuf = _kernel32.MapViewOfFile(
        hFileMappingObject,
        _wt.DWORD(dwDesiredAccess),
        _wt.DWORD(dwFileOffsetHigh),
        _wt.DWORD(dwFileOffsetLow),
        _wt.DWORD(dwNumberOfBytesToMap)
    )
    if pBuf == 0:
        raise error_from_winerror(_winapi.GetLastError())
    return pBuf


class _MEMORY_BASIC_INFORMATION(BetterStruct):
    _fields_ = (
        ('BaseAddress', _ctypes.c_void_p),
        ('AllocationBase', _ctypes.c_void_p),
        ('AllocationProtect', _wt.DWORD),
        ('PartitionId', _wt.WORD),
        ('RegionSize', _wt.PULONG),
        ('State', _wt.DWORD),
        ('Protect', _wt.DWORD),
        ('Type', _wt.DWORD)
    )
    def __init__(self,
                 BaseAddress=0,
                 AllocationBase=0,
                 AllocationProtect=0,
                 PartitionId=0,
                 RegionSize=0,
                 State=0,
                 Protect=0,
                 Type=0
                 ):
        super().__init__()
        self.BaseAddress = BaseAddress
        self.AllocationBase = AllocationBase
        self.AllocationProtect = AllocationProtect
        self.PartitionId = PartitionId
        self.RegionSize = RegionSize
        self.State = State
        self.Protect = Protect
        self.Type = Type


def _VirtualQuerySize(
        lpAddress
):
    memInfo = _MEMORY_BASIC_INFORMATION()

    nBytes = _kernel32.VirtualQuery(
        lpAddress,
        _ctypes.byref(memInfo),
        _ctypes.sizeof(memInfo)
    )

    if nBytes == 0:
        raise error_from_winerror(_winapi.GetLastError())

    return memInfo.RegionSize.contents


def _random_filename():
    """Create a random filename for the shared memory object."""
    # number of random bytes to use for name
    nbytes = (SHM_SAFE_NAME_LENGTH - len(SHM_NAME_PREFIX)) // 2
    assert nbytes >= 2, '_SHM_NAME_PREFIX too long'
    name = SHM_NAME_PREFIX + _helpers.random_hex(nbytes)
    assert len(name) <= _SHM_SAFE_NAME_LENGTH
    return name


def shared_memory(id_, size, create=False):
    if create:
        while True:
            id_ = random.randint(0, 0xFFFFFFFF) if id_ is None else id_
            temp_name = _helpers.nameof(id_)
            hFile = INVALID_HANDLE_VALUE
            flProtect = PAGE_READWRITE
            dwMaximumSizeHigh = (size >> 32) & 0xFFFFFFFF
            dwMaximumSizeLow = size & 0xFFFFFFFF
            lpName = temp_name

            try:
                hMap = Handle(_CreateFileMapping(hFile, flProtect, dwMaximumSizeHigh, dwMaximumSizeLow, lpName))

            except OSError as e:
                if e.winerror == ERROR_ALREADY_EXISTS:
                    if id_ is not None:
                        raise winerror_last() from None
                    continue
                return -1, size, {'tagname': temp_name}, id_

    else:
        if id_ is None:
            raise ValueError("Shared memory must be passed an id upon opening.")
        name = _helpers.nameof(id_)

        try:
            hMap = Handle(_OpenFileMapping(FILE_MAP_READ, name))
        except OSError:
            raise winerror_last() from None

        try:
            pBuf = _MapViewOfFile(
                hMap,
                FILE_MAP_READ,
                0,
                0,
                0
            )
        except OSError:
            raise winerror_last()

        try:
            size = _VirtualQuerySize(pBuf)
        except OSError:
            raise winerror_last() from None

        return -1, size, {'tagname': name}, id_


def unmap(buf, mmap, fd):
    if buf is not None:
        buf.release()
    if mmap is not None:
        mmap.close()


@_NoPath
class DeviceError(WindowsError):
    """
    Something went wrong with a specific device.
    """
    pass


# map windows error codes to python exception types, if possible:
_winerr_types = {
    1: ValueError,
    2: FileNotFoundError,
    3: FileNotFoundError,
    5: PermissionError,
    6: ValueError,
    7: MemoryError,
    8: OverflowError,
    10: EnvironmentError,
    13: ValueError,
    14: OverflowError,
    16: PermissionError,
    19: PermissionError,
    21: DeviceError,
    22: SyntaxError,
    23: RecursionError,
    28: DeviceError,
    29: PermissionError,
    30: PermissionError,
    31: DeviceError,
    32: ProcessLookupError,
    33: ProcessLookupError,
    34: DeviceError,
    36: OverflowError,
    38: EOFError,
    39: OverflowError,
    50: ConnectionError,
    51: ConnectionError,
    52: NameError,
    53: ConnectionError,
    54: TimeoutError,
    55: FileNotFoundError,
    56: OverflowError,
    60: DeviceError,
    61: DeviceError,
    63: FileNotFoundError,
    64: NameError,
    65: PermissionError,
    66: TypeError,
    67: NameError,
    68: OverflowError,
    69: OverflowError,
    70: ConnectionRefusedError,
    71: ConnectionRefusedError,
    72: DeviceError,
    80: FileExistsError,
    82: PermissionError,
    84: OverflowError,
    85: NameError,
    86: ConnectionAbortedError,
    87: ValueError,
    88: PermissionError,
    89: OverflowError,
    100: OverflowError,
    101: PermissionError,
    108: PermissionError,
    109: BrokenPipeError,
    111: NameError,
    112: OverflowError,
    114: ValueError,
    119: NotImplementedError,
    120: NotImplementedError,
    121: TimeoutError,
    122: MemoryError,
    123: SyntaxError,
    126: ReferenceError,
    127: ReferenceError,
    128: ChildProcessError,
    131: ValueError,
    155: OverflowError,
    164: OverflowError,
    170: PermissionError,
    182: ValueError,
    183: FileExistsError,
    186: ValueError,
    194: OverflowError,
    195: MemoryError,
    199: OverflowError,
    200: OverflowError
}

