"""
Process implementation for posix platforms.
"""

import _thread
import _posixsubprocess
import os
import signal
import time

from .._typing import *
from .._const import *
from .._errors import *


STILL_ACTIVE = 259


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


def _ensure_fd_not_std(fd):
    """
    Make sure fd is not in the range of standard io
    """
    low_fds_to_close = []
    while fd < 3:
        low_fds_to_close.append(fd)
        fd = os.dup(fd)
    for low_fd in low_fds_to_close:
        os.close(low_fd)
    return fd


def _spawnv(path, args, fd_keep_open, working_dir, env_vars, pre_exec):
    """
    Spawn a new process.
    """
    p2c = os.pipe()
    c2p = os.pipe()
    errors = os.pipe()

    errpipe = os.pipe()
    errpipe = (errpipe[0], _ensure_fd_not_std(errpipe[1]))

    tid_lock = _thread.allocate_lock()

    tid = 0

    proc_stdin = create_new_pipe()
    proc_stdout = create_new_pipe()

    def _pre_exec():
        tid_lock.acquire()
        globals()['tid'] = _thread.get_ident()
        tid_lock.release()
        pre_exec()

    try:
        # noinspection PyTypeChecker
        pid = _posixsubprocess.fork_exec(args, [os.fsencode(path)], True, fd_keep_open, working_dir,
                                         env_vars, *proc_stdin, *proc_stdout, *errors, *errpipe, False, False,
                                         None, None, None, -1, _pre_exec)
    finally:
        # close pipe sides we aren't meant to own, no matter what:
        os.close(errpipe[0])
        os.close(p2c[1])
        os.close(c2p[0])
        os.close(errors[0])
        os.close(errpipe[0])

    if pid == 0:
        raise ProcessStartupError("Failed to start the process.", reason='pid == 0')

    time.sleep(0.01)
    # wait until tid has been set by the process:
    tid_lock.acquire()
    tid_lock.release()

    if tid == 0:
        raise ProcessStartupError("Failed to initialize primary thread.")

    pipes = c2p[0], p2c[1], errpipe[0]  # in, out, err
    return (pid, None), (tid, None), pipes


def start_new_process(command, options):
    """
    Start new process.
    Returns (process_info, thread_id, pipes);  where:

    - process_info is a tuple of process id, None and process standard io (None is there for platform compatibility)
    - thread_id is the process primary thread's id
    - pipes is a tuple of the process communication streams read, write and error
    """
    path, args = command.split(' ', maxsplit=1)
    keepfds = options.get_option('keepfds', ())
    workdir = options.get_option('curdir', '')
    env = options.get_option('environ', os.environ.copy())
    pre_exec = options.get_option('preexec', NO_OP)

    if workdir == '':
        workdir = None

    return _spawnv(path, args, keepfds, workdir, env, pre_exec)


def execute_command(command, options=None, curdir=None):
    """
    Execute a command in shell.
    Same return values as start_new_process
    """
    if options is None:
        options = ProcessStartOptions()
        options.curdir = os.curdir if curdir is None else curdir

    cmd = f"{SHELL} -c \"{command}\""
    return start_new_process(cmd, options)


def create_new_pipe():
    """
    Create a new pipe and return a pair of read and write inheritable handles.
    """
    return os.pipe()


def close_descr(descr):
    os.close(descr)


def read_descr(descr, size):
    return os.read(descr, size)


def write_descr(descr, data):
    return os.write(descr, data)


def terminate_process(pid):
    """
    Attempt to terminate a process.
    Return whether this function succeeded.
    """
    try:
        os.kill(pid, signal.SIGTERM)
    except PermissionError:
        return False
    return True


def kill_process(pid):
    """
    Attempt to kill a process.
    Return whether this function has succeeded.
    """
    try:
        os.kill(pid, signal.SIGKILL)
    except PermissionError:
        return False
    return True


def get_current_process():
    """
    Return the current process' pid.
    """
    return os.getpid()


def get_process_exit_code(pid):
    pid, status = os.waitpid(pid, os.WNOHANG)
    if os.WIFEXITED(status):
        # noinspection PyUnresolvedReferences
        return os.waitstatus_to_exitcode(status)
    if os.WIFSTOPPED(status):
        return -1
    return STILL_ACTIVE

