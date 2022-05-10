"""
Process implementation for Windows platforms.
"""
import contextlib
import os

from .._typing import *
from .._const import *
from .._errors import *

import subprocess
import _winapi
import msvcrt

_PIPE = -1
_STDOUT = -2
_DEVNULL = -3

_FILE_TYPE_CHAR = 2


def _filter_handle_list(handle_list):
    # borrowed from subprocess module
    return list({handle for handle in handle_list
                 if handle & 0x3 != 0x3
                 or _winapi.GetFileType(handle) !=
                 _FILE_TYPE_CHAR})


class ProcessStartupInfo:
    # borrowed from subprocess module
    def __init__(self, *, dwFlags=0, hStdInput=None, hStdOutput=None,
                 hStdError=None, wShowWindow=0, lpAttributeList=None):
        self.dwFlags = dwFlags
        self.hStdInput = hStdInput
        self.hStdOutput = hStdOutput
        self.hStdError = hStdError
        self.wShowWindow = wShowWindow
        self.lpAttributeList = lpAttributeList or {"handle_list": []}

    def copy(self):
        attr_list = self.lpAttributeList.copy()
        if 'handle_list' in attr_list:
            attr_list['handle_list'] = list(attr_list['handle_list'])

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
        _winapi.CloseHandle(self)

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
    Returns (process_info, thread_id, pipes);  where:

    - process_info is a tuple of process handle and process id
    - thread_id is the process primary thread's id
    - pipes is a tuple of the process communication streams read, write and error
    """
    parent_to_child = options.get_option("p2c", os.pipe())
    child_to_parent = options.get_option("c2p", os.pipe())
    error_stream = options.get_option("err", os.pipe())
    startupinfo = options.get_option("startupinfo", ProcessStartupInfo())
    flags = options.get_option("flags", 0)
    env_vars = options.get_option("environment_vars", {})
    curdir = options.get_option("curdir", "")
    close_fds = options.get_option("close_fds", True)

    if curdir == "":
        curdir = None

    startupinfo = startupinfo.copy()

    use_std_handles = -1 not in (parent_to_child[0], child_to_parent[1], error_stream[1])
    if use_std_handles:
        startupinfo.dwFlags |= _winapi.STARTF_USESTDHANDLES
        startupinfo.hStdInput = parent_to_child[0]
        startupinfo.hStdOutput = child_to_parent[1]
        startupinfo.hStdError = error_stream[1]

    attribute_list = startupinfo.lpAttributeList
    have_handle_list = bool(attribute_list and "handle_list" in attribute_list and attribute_list["handle_list"])

    if have_handle_list or (use_std_handles and close_fds):
        if attribute_list is None:
            attribute_list = startupinfo.lpAttributeList = {}
        handle_list = attribute_list["handle_list"] = \
            list(attribute_list.get("handle_list", []))

        if use_std_handles:
            handle_list += [int(parent_to_child[0]), int(child_to_parent[1]), int(error_stream[1])]

    err = None
    tid, pid = 0, 0
    proc_h, thread_h = Handle(0), Handle(0)
    try:
        proc_h, thread_h, pid, tid = _winapi.CreateProcess(
            None,
            command,
            None, None,
            int(not close_fds),
            flags,
            env_vars,
            curdir,
            startupinfo
        )
    except WindowsError as e:
        err = e.strerror, e.winerror

    finally:
        with contextlib.ExitStack() as s:
            s.callback(os.close, parent_to_child[0])
            s.callback(os.close, child_to_parent[1])
            s.callback(os.close, error_stream[1])

    if err is not None:
        raise ProcessStartupError(err[0], f'(code {hex(err[1])})')

    proc_info = pid, Handle(proc_h),
    Handle(thread_h).close()
    pipes = child_to_parent[0], parent_to_child[1], error_stream[0]  # in, out, err

    return proc_info, tid, pipes


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


