"""
Process implementation for Windows platforms.
Important:
    Some code in here is borrowed from the subprocess or multiprocessing modules.
"""
import contextlib
import io
import os
import sys

from .._typing import *
from .._const import *
from .._errors import *

import _winapi
import ctypes as _ctypes
from ctypes import wintypes as _wt


_kernel32 = _ctypes.WinDLL('kernel32.dll')


_kernel32.GetCurrentProcessId.restype = _wt.DWORD


STILL_ACTIVE = 259


_PIPE = -1
_STDOUT = -2
_DEVNULL = -3

_FILE_TYPE_CHAR = 2

SW_SHOW = 5


_all_processes = {}


class ProcessStartupInfo:
    # borrowed from subprocess module
    def __init__(self, *, dwFlags=0, hStdInput=None, hStdOutput=None,
                 hStdError=None, wShowWindow=_winapi.SW_HIDE, lpAttributeList=None):
        self.dwFlags = dwFlags
        self.hStdInput = hStdInput
        self.hStdOutput = hStdOutput
        self.hStdError = hStdError
        self.wShowWindow = wShowWindow
        self.lpAttributeList = lpAttributeList

    def copy(self):
        attr_list = self.lpAttributeList.copy() if self.lpAttributeList is not None else None

        return ProcessStartupInfo(dwFlags=self.dwFlags,
                                  hStdInput=self.hStdInput,
                                  hStdOutput=self.hStdOutput,
                                  hStdError=self.hStdError,
                                  wShowWindow=self.wShowWindow,
                                  lpAttributeList=attr_list)


class Handle(int):
    # borrowed from subprocess module
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._closed = False

    def close(self):
        if not self._closed:
            self._closed = True
            try:
                _winapi.CloseHandle(self)
            except OSError:
                pass

    def detach(self):
        if not self._closed:
            self._closed = True
            return int(self)
        raise ValueError("already closed")

    def __repr__(self):
        return f"<handle {int(self)} at {hex(id(self))}>"

    def __del__(self):
        self.close()

    closed = property(lambda self: self._closed)


class ProcessStartOptions:
    def __init__(self, **options):
        for name, opt in options.items():
            setattr(self, name, opt)
        
    def get_option(self, name, default=None):
        val = default
        try:
            val = getattr(self, name)
        except:
            pass
        if (val is not None) and (default is not None):
            type_check((val,), type(default))
        return val


def start_new_process(command, options):
    """
    Start new process.
    Returns (process_info, thread_info, pipes);  where:

    - process_info is a tuple of process id, process handle and process standard io
    - thread_info is a tuple of the primary thread's id and a handle to it
    - pipes is a tuple of the process communication streams read, write and error
    """
    parent_to_child = options.get_option("p2c", create_new_pipe())
    child_to_parent = options.get_option("c2p", create_new_pipe())
    error_stream = options.get_option("err", create_new_pipe())
    startupinfo = options.get_option("startupinfo", ProcessStartupInfo())
    flags = options.get_option("flags", 0)
    env_vars = options.get_option("environ", {})
    curdir = options.get_option("curdir", "")
    close_fds = options.get_option("close_fds", True)
    create_console = options.get_option('create_console', False)

    if curdir == "":
        curdir = None
    if env_vars == {}:
        env_vars = None

    startupinfo = startupinfo.copy()

    proc_stdin = create_new_pipe()
    proc_stdout = create_new_pipe()

    use_std_handles = -1 not in (parent_to_child[0], child_to_parent[1], error_stream[1])
    if use_std_handles:
        startupinfo.dwFlags |= _winapi.STARTF_USESTDHANDLES
        startupinfo.hStdInput = proc_stdin
        startupinfo.hStdOutput = proc_stdout
        startupinfo.hStdError = error_stream[1]
    if startupinfo.wShowWindow > 0:
        startupinfo.dwFlags |= _winapi.STARTF_USESHOWWINDOW

    if create_console:
        flags |= _winapi.CREATE_NEW_CONSOLE

    attribute_list = startupinfo.lpAttributeList
    have_handle_list = bool(attribute_list and "handle_list" in attribute_list and attribute_list["handle_list"])

    if have_handle_list or (use_std_handles and close_fds):
        if attribute_list is None:
            attribute_list = startupinfo.lpAttributeList = {}
        handle_list = attribute_list["handle_list"] = \
            list(attribute_list.get("handle_list", []))

        if use_std_handles:
            handle_list += [int(parent_to_child[0]), int(child_to_parent[1]), int(error_stream[1])]

    try:
        proc_h, thread_h, pid, tid = _winapi.CreateProcess(
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
        raise ProcessStartupError(e.strerror + f' (WinError {e.winerror}, {hex(e.winerror)})') from None

    finally:
        if close_fds:
            with contextlib.ExitStack() as s:
                s.callback(_winapi.CloseHandle, parent_to_child[0])
                s.callback(_winapi.CloseHandle, child_to_parent[1])
                s.callback(_winapi.CloseHandle, error_stream[1])

    proc_info = pid, Handle(proc_h), (proc_stdin, proc_stdout)
    # Handle(thread_h).close()
    th_info = (tid, Handle(thread_h))
    pipes = child_to_parent[0], parent_to_child[1], error_stream[0]  # in, out, err

    _all_processes[pid] = proc_h

    return proc_info, th_info, pipes


def execute_command(command, options=None, curdir=None):
    """
    Execute a command in shell.
    Same return values as start_new_process
    """
    if options is None:
        options = ProcessStartOptions()
        options.curdir = os.curdir if curdir is None else curdir
        options.startupinfo = ProcessStartupInfo()
        options.startupinfo.dwFlags |= _winapi.STARTF_USESHOWWINDOW
        options.startupinfo.wShowWindow = _winapi.SW_HIDE

    return start_new_process(f"{SHELL} /c \"{command}\"", options)


def create_new_pipe():
    """
    Create a new pipe and return a pair of read and write inheritable handles.
    """
    pipe = _winapi.CreatePipe(None, 0)
    # make handles inheritable:
    # *following code borrowed from subprocess module*:
    read = _winapi.DuplicateHandle(
        _winapi.GetCurrentProcess(),
        pipe[0],
        _winapi.GetCurrentProcess(),
        0,
        True,
        _winapi.DUPLICATE_SAME_ACCESS
    )
    write = _winapi.DuplicateHandle(
        _winapi.GetCurrentProcess(),
        pipe[1],
        _winapi.GetCurrentProcess(),
        0,
        True,
        _winapi.DUPLICATE_SAME_ACCESS
    )
    return read, write


def close_descr(descr):
    _winapi.CloseHandle(descr)


def read_descr(descr, size):
    res = _winapi.ReadFile(descr, size)
    return res[1]


def write_descr(descr, data):
    return _winapi.WriteFile(descr, data)


def terminate_process(pid):
    """
    Attempt to terminate a process.
    Return whether this function succeeded.
    """
    if pid not in _all_processes:
        hproc = _winapi.OpenProcess(0, True, pid)
    else:
        hproc = _all_processes[pid]

    try:
        _winapi.TerminateProcess(hproc, -1)
    except:
        return False
    return True


def kill_process(pid):
    """
    Attempt to kill a process.
    Return whether this function has succeeded.
    """
    return terminate_process(pid)


def get_current_process():
    """
    Return the current process' pid.
    """
    pid: _wt.DWORD = _kernel32.GetCurrentProcessId()
    try:
        return pid.value
    except:
        return pid


def get_process_exit_code(pid):
    try:
        if pid not in _all_processes:
            hproc = _winapi.OpenProcess(0, True, pid)
        else:
            hproc = _all_processes[pid]

        ecode = _winapi.GetExitCodeProcess(hproc)
        return STILL_ACTIVE if ecode == _winapi.STILL_ACTIVE else ecode
    except OSError as e:
        raise ProcessLookupError(*e.args) from None

