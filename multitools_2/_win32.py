import _winapi
import errno as _errno
import os
import ctypes as _ctypes
from ctypes import wintypes as _wt


from ._errors import _NoPath

# print(locale.setlocale(locale.LC_NUMERIC, 'en_US'))

_kernel32 = _ctypes.WinDLL('kernel32.dll')


SW_HIDE = 0
STARTF_USESTDHANDLES = 256
CREATE_NEW_CONSOLE = 16

FORMAT_MESSAGE_ALLOCATE_BUFFER = 0x00000100
FORMAT_MESSAGE_FROM_SYSTEM = 0x00001000
FORMAT_MESSAGE_IGNORE_INSERTS = 0x00000200

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


ERROR_ACCESS_DENIED = 5
ERROR_WRITE_PROTECT = 19
ERROR_SHARING_VIOLATION = 32
ERROR_INVALID_PARAMETER = 87


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
        self.check_open()
        if not self._closed:
            self._closed = True
            return int(self)
        raise ValueError("already closed")

    def duplicate(self, inheritable=False):
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
        if self._closed:
            raise ValueError('Closed handle.')

    def __reduce__(self):
        return (self.__class__,
                (int(self),)
                )

    def __repr__(self):
        return f"<handle {int(self)} at {hex(id(self))}>"

    def __del__(self):
        self.close()

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


class StartupInfo:
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
    Close a stream associated with a file descriptor or handle.
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


def open_process(pid):
    """
    Open the process of given id and return a handle to it.
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

