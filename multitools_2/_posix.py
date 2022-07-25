import _posixsubprocess
import os
import random
import signal
import sys
import _posixshmem

from . import _helpers


"""
shared memory:
import _posixshmem
"""


SHM_NAME_PREFIX = '/psm_'
SHM_SAFE_NAME_LENGTH = 14


def terminate(pid):
    try:
        os.kill(pid, signal.SIGTERM)
    except PermissionError:
        return False
    except:
        raise
    return True


def kill(pid):
    try:
        os.kill(pid, signal.SIGKILL)
    except PermissionError:
        return False
    except:
        raise
    return True


def join(pid):
    _, code = os.waitpid(pid, 0)
    return code


def exit_status(pid):
    _pid, code = os.waitpid(pid, os.WNOHANG)
    if _pid == 0:
        return
    return code


def spawnv(path, args, fd_keep_open, working_dir, env_vars, pre_exec, pipes):
    p2c = pipes[0]
    c2p = pipes[1]
    errors = pipes[2]
    exc_info_pipe = pipes[3]

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

    pipes = c2p[1], p2c[0], errpipe[0], exc_info_pipe[0]  # in, out, err, exc_info
    return (pid, None), (tid, None), pipes


def process(command, options):
    path, args = command.split(' ', maxsplit=1)
    keepfds = options.get_option('keepfds', ())
    workdir = options.get_option('curdir', '')
    env = options.get_option('environ', os.environ.copy())
    pre_exec = options.get_option('preexec', NO_OP)

    p2c_pipe = options.get_option('p2c', None)
    c2p_pipe = options.get_option('c2p', None)
    err_pipe = options.get_option('err', None)
    exc_info_pipe = options.get_option('exc_info_pipe', pipe())

    if workdir == '':
        workdir = None

    return spawnv(path, args, keepfds, workdir, env, pre_exec, (p2c_pipe, c2p_pipe, err_pipe, exc_info_pipe))


def _random_filename():
    """Create a random filename for the shared memory object."""
    # number of random bytes to use for name
    nbytes = (SHM_SAFE_NAME_LENGTH - len(SHM_NAME_PREFIX)) // 2
    assert nbytes >= 2, '_SHM_NAME_PREFIX too long'
    name = SHM_NAME_PREFIX + _helpers.random_hex(nbytes)
    assert len(name) <= _SHM_SAFE_NAME_LENGTH
    return name


"""def shared_memory(name, size, create=False):
    mode = 0o600
    flags = os.O_RDWR if not create else (os.O_CREAT | os.O_EXCL) | os.O_RDWR

    fd = None

    if name is None:
        name = _random_filename()
        while True:
            try:
                fd = _posixshmem.shm_open(
                    name,
                    flags,
                    mode=mode
                )
            except FileExistsError:
                continue
            break
    else:
        name = '/' + name
        fd = _posixshmem.shm_open(
            name,
            flags,
            mode=mode
        )
    try:
        if create and size:
            os.ftruncate(fd, size)
        stats = os.fstat(fd)
        size = stats.st_size
        return fd, size, {}, name
    except OSError:
        os.close(fd)
        raise"""


def shared_memory(id_, size, create=False):
    mode = 0o600
    flags = os.O_RDWR if not create else (os.O_CREAT | os.O_EXCL) | os.O_RDWR

    fd = None

    if id_ is None:
        while True:
            name = nameof(random.randint(0, 0xFFFFFFFF))
            try:
                fd = _posixshmem.shm_open(
                    name,
                    flags,
                    mode=mode
                )
            except FileExistsError:
                continue
            break
    else:
        name = '/' + _helpers.nameof(id_)
        fd = _posixshmem.shm_open(
            name,
            flags,
            mode=mode
        )

    try:
        if create and size:
            os.ftruncate(fd, size)
        stats = os.fstat(fd)
        size = stats.st_size
        return fd, size, {}, id_
    except OSError:
        os.close(fd)
        raise


def unmap(buf, mmap, fd):
    if buf is not None:
        buf.release()
    if mmap is not None:
        mmap.close()
    os.close(fd)


raw_stdin = sys.stdin.fileno()

raw_stdout = sys.stdout.fileno()

raw_stderr = sys.stderr.fileno()
