"""
Process implementation for Windows platforms.
Important:
    Some code in here is borrowed from the subprocess or multiprocessing modules.
"""
import contextlib
import io
import os
import sys

from .._relay import *
from .._relay import _win32

import _winapi
import ctypes as _ctypes
from ctypes import wintypes as _wt


_MAX_UINT32_VAL = 4294967295


_kernel32 = _ctypes.WinDLL('kernel32.dll')


_kernel32.GetCurrentProcessId.restype = _wt.DWORD


STILL_ACTIVE = 259


_PIPE = -1
_STDOUT = -2
_DEVNULL = -3

_FILE_TYPE_CHAR = 2

SW_SHOW = 5
SW_HIDE = 0

_PROCESS_QUERY_INFORMATION = 0x0400
_ERROR_INVALID_PARAMETER = 87


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


def _get_handle_proc(proc, handle=False):
    if handle:
        return proc
    try:
        return _win32.Handle(_winapi.OpenProcess(_PROCESS_QUERY_INFORMATION, True, proc))
    except WindowsError as e:
        if e.winerror == _ERROR_INVALID_PARAMETER:
            print('invalid parameter:', proc)
            return None
        raise


def start_new_process(command, options):
    """
    Start new process.
    Returns (process_info, thread_info, pipes);  where:

    - process_info is a tuple of process id, process handle and process standard io
    - thread_info is a tuple of the primary thread's id and a handle to it
    - pipes is a tuple of the process communication streams read, write and error as well as a pipe that will receive
    the process exc_info()
    """
    """parent_to_child = options.get_option("p2c", create_new_pipe())
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
            startupinfo.hStdInput = proc_stdin[0]
            startupinfo.hStdOutput = proc_stdout[1]
            startupinfo.hStdError = error_stream[1]

        if startupinfo.wShowWindow > 0:
            startupinfo.dwFlags |= _winapi.STARTF_USESHOWWINDOW

        proc_stderr = error_stream[1] if error_stream[1] >= 1 else _win32.pipe()
        startupinfo.hStdError = proc_stderr

        if not create_console:
            proc_stdin = parent_to_child[0] if parent_to_child[0] >= 0 else _win32.pipe()
            proc_stdout = child_to_parent[1] if child_to_parent[1] >= 0 else _win32.pipe()

            startupinfo.dwFlags |= _winapi.STARTF_USESTDHANDLES
            startupinfo.hStdInput = proc_stdin
            startupinfo.hStdOutput = proc_stdout

        else:
            flags |= _winapi.CREATE_NEW_CONSOLE

        attribute_list = startupinfo.lpAttributeList
        have_handle_list = bool(attribute_list and "handle_list" in attribute_list and attribute_list["handle_list"])

        use_std_handles = (-1 not in parent_to_child[0], child_to_parent[1], error_stream[1])
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

        proc_info = pid, _win32.Handle(proc_h), (proc_stdin, proc_stdout)
        # Handle(thread_h).close()
        th_info = (tid, _win32.Handle(thread_h))
        pipes = child_to_parent[0], parent_to_child[1], error_stream[0]  # in, out, err

        _all_processes[pid] = proc_h

        return proc_info, th_info, pipes"""
    p2c_pipe = options.get_option("p2c", None)
    c2p_pipe = options.get_option("c2p", None)
    err_pipe = options.get_option("err", None)
    exc_info_pipe = options.get_option("exc_info_pipe", _win32.pipe())
    startupinfo = options.get_option("startupinfo", _win32.StartupInfo())
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


    attribute_list = startupinfo.lpAttributeList
    have_handle_list = bool(attribute_list and "handle_list" in attribute_list and attribute_list["handle_list"])

    if startupinfo.wShowWindow != 0:
        startupinfo.dwFlags |= _winapi.STARTF_USESHOWWINDOW

    if use_std_handles:
        p2c_pipe = p2c_pipe if p2c_pipe is not None else _win32.pipe()
        c2p_pipe = c2p_pipe if c2p_pipe is not None else _win32.pipe()
        err_pipe = err_pipe if err_pipe is not None else _win32.pipe()

        proc_stdin_called, proc_stdin_caller = p2c_pipe
        proc_stdout_caller, proc_stdout_called = c2p_pipe
        proc_stderr_caller, proc_stderr_called = err_pipe

        startupinfo.dwFlags |= _win32.STARTF_USESTDHANDLES
        startupinfo.hStdInput = proc_stdin_called
        startupinfo.hStdOutput = proc_stdout_called
        startupinfo.hStdError = proc_stderr_called

    else:
        flags |= _win32.CREATE_NEW_CONSOLE


    if have_handle_list or (use_std_handles and close_fds):
        if attribute_list is None:
            attribute_list = startupinfo.lpAttributeList = {}
        handle_list = attribute_list["handle_list"] = list(attribute_list.get("handle_list", []))

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
        raise ProcessStartupError(e.strerror + f' (WinError {e.winerror}, {hex(e.winerror)})') from None

    finally:
        with contextlib.ExitStack() as s:
            s.callback(_winapi.CloseHandle, called_exc_info_pipe)
            if use_std_handles:
                s.callback(_winapi.CloseHandle, proc_stdin_called)
                s.callback(_winapi.CloseHandle, proc_stdout_called)
                s.callback(_winapi.CloseHandle, proc_stderr_called)
                if close_fds:
                    s.callback(_winapi.CloseHandle, proc_stdin_caller)
                    s.callback(_winapi.CloseHandle, proc_stdout_caller)
                    s.callback(_winapi.CloseHandle, proc_stderr_caller)

    caller_pipes = (caller_exc_info_pipe,) if not use_std_handles else (
        proc_stdin_caller,
        proc_stdout_caller,
        proc_stderr_caller,
        caller_exc_info_pipe
    )
    proc_info = process_id, _win32.Handle(process_handle)
    thread_info = thread_id, _win32.Handle(thread_handle)
    return proc_info, thread_info, caller_pipes


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
    return _win32.pipe()


def open_process(pid):
    if isinstance(pid, _win32.Handle):
        return pid
    return _get_handle_proc(pid)


def close_descr(descr):
    _winapi.CloseHandle(descr)


def read_descr(descr, size):
    res = _winapi.ReadFile(descr, size)
    return res[1]


def write_descr(descr, data):
    return _winapi.WriteFile(descr, data)


def terminate_process(proc, handle=False):
    """
    Attempt to terminate a process.
    Return whether this function succeeded.
    """
    hproc = _get_handle_proc(proc, handle=handle)
    if hproc is None:
        return False

    try:
        _winapi.TerminateProcess(hproc, -1)
    except:
        return False
    return True


def kill_process(proc, handle=False):
    """
    Attempt to kill a process.
    Return whether this function has succeeded.
    """
    return terminate_process(proc, handle=handle)


def get_current_process():
    """
    Return the current process' pid.
    """
    pid: _wt.DWORD = _kernel32.GetCurrentProcessId()
    try:
        return pid.value
    except:
        return pid


def get_process_exit_code(proc, handle=False):
    """
    Return immediately a process' exit status.
    If the process is still running, return STILL_ACTIVE.
    """
    hproc = _get_handle_proc(proc, handle=handle)
    if hproc is None:
        return
    try:
        ecode = _winapi.GetExitCodeProcess(hproc)
    except WindowsError as e:
        # to do adapt error to e.winerror
        raise ProcessLookupError(*e.args) from None

    if (ecode != STILL_ACTIVE) and ((_MAX_UINT32_VAL / 2) <= ecode <= _MAX_UINT32_VAL):
        diff = (_MAX_UINT32_VAL + 1) - ecode
        ecode = -diff

    return STILL_ACTIVE if ecode == _winapi.STILL_ACTIVE else ecode


def get_proc_exc_info(c2p):
    """
    Return exc_info() from the process. Only works once the process is terminated.
    **Warning: this function doesn't actually work because of a bug in the bytes constructor.**
    """
    try:
        if not _winapi.PeekNamedPipe(c2p, 4)[-2]:  # no bytes available to be read
            return None, None
    except BrokenPipeError:
        return None
    head = _winapi.ReadFile(c2p, 4)
    try:
        size = int.from_bytes(head, 'big')
    except TypeError:
        print("[multitools] Warning: Process.exc_info() function doesn't actually work because of a bug in the bytes constructor.", file=sys.stderr)
        return None
    data = _winapi.ReadFile(c2p, size)
    exc_info = pickle.loads(data[0])
    return exc_info

