import _winapi
import io
import time
import types as _types
from .. import io as _io

from .._meta import MultiMeta
from .._const import *
from .._errors import *
from .._helpers import *
from .._typing import type_check as _type_check
from . import _platform_impl as _impl
from . import _thread
from .. import _win32


_blocking_processes = {}  # list of all non-daemon processes.
_pthreads_info = {}  # record of all known threads, sorted per known process id.


def _pickle_obj(obj, proto=4):
    import io
    f = io.BytesIO()
    pickler = pickle.Pickler(f, protocol=proto)
    return pickler.dump(obj)


def _build_proc_code(child_pipes, proc_obj, call_args, call_kwargs):
    """
    Construct and return a process code string, given pipes, process and call arguments.
    """
    try:
        p_args = pickle.dumps(call_args)
    except pickle.PickleError:
        raise ValueError("Arguments must pickleable.") from None

    try:
        p_kwargs = pickle.dumps(call_kwargs)
    except pickle.PickleError:
        raise ValueError("Keyword arguments must be pickleable.") from None

    # split pickled data's repr into multiple segments to avoid line size limitations:
    all_data = repr(proc_obj)
    b_size = len(all_data)
    proc_b_setter = "b'"
    proc_obj_count = int(b_size / 2000) + 1  # round to higher int value
    start = 0
    end = 2000
    for i in range(proc_obj_count):
        data = all_data[start:end]
        last_bytes = data[-3:]
        if '\\' in last_bytes:  # check for escape codes
            mov_amount = 3 - last_bytes.find('\\')
            end -= mov_amount
            data = all_data[start:end]

        po = data.removeprefix("b'").removesuffix("'")
        proc_b_setter += po
        proc_b_setter += "' \\\n    + b'"

        start = end
        end += 2000
    proc_b_setter = proc_b_setter.removesuffix(" \\\n    + b'")

    # code to be run by the process:
    return f"""
import pickle, os, sys, time, _thread, io
_WINDOWS = True
try:
    import _winapi
except ModuleNotFoundError or ImportError:
    _WINDOWS = False
p2c, c2p, err, exc_info_pipe = ({int(child_pipes[0])}, {int(child_pipes[1])}, {int(child_pipes[2])}, {child_pipes[3]})
# sys.stderr.write(str(p2c))
time.sleep(0.1)
proc_b = {proc_b_setter}
# print('new process:', proc_b, file=sys.stderr)
# proc_obj = pickle.loads(proc_b)
f = io.BytesIO(proc_b)
proc_obj = pickle.Unpickler(f).load()

setattr(proc_obj, '#id', os.getpid())
setattr(proc_obj, '#state', 1)
setattr(proc_obj, '#known_threads', (_thread.get_ident(),))

args = pickle.loads({repr(p_args)})
kwargs = pickle.loads({repr(p_kwargs)})
target_function = getattr(proc_obj, '#target')

exc_info = (None, None)
try:
    exit_code = target_function(proc_obj, *args, **kwargs)
except SystemExit as e:
    exit_code = e.code
except KeyboardInterrupt:
    exit_code = -1
except:
    exc_info = sys.exc_info()[0], sys.exc_info()[1]
    sys.excepthook(*sys.exc_info())
    
    exc_info_p = pickle.dumps(exc_info)
    if _WINDOWS:
        _winapi.WriteFile(exc_info_pipe, len(exc_info_p).to_bytes(4, 'big'))
        _winapi.WriteFile(exc_info_pipe, exc_info_p)  
    else:
        os.write(exc_info_pipe, len(exc_info_p).to_bytes(4, 'big'))
        os.write(exc_info_pipe, exc_info_p)  
    
    raise SystemExit(1) from None

if (exit_code is None) or not isinstance(exit_code, int):
    exit_code = 0
raise SystemExit(exit_code) from None
"""


class Process(metaclass=MultiMeta):
    """
    Class representing processes.

    A Process instance can be in 3 main states:
    - state 0 ('initialized'): The object is a model from which multiple processes can be started by calling it.
    This state is returned when instantiating the Process class.
    - state 1 ('running'): The object represents the activity of a running process on the system. This state is
    returned when a process is started or opened.
    - state 2 ('finalized'): The object represents a process that has already terminated. State 1 objects take
    this state when their attached process ends.


    Process models (state 0) are objects containing information about one or more future processes, passed in
    as parameters to the class constructor. They store activity for the process to execute, as well as various
    options to customize the processes to be started. Activity can be either a python function or a shell
    command to be executed. When called, these start a process using information they store and return a
    process activity (state 1) object containing information about the newly started process.

    A process activity (state 1) is an object that represents an active process on the system. It stores
    various information about the process execution such as its pid. This state is returned by the call
    of a process model and by the __open__() class method. When its associated process has finished
    executing, gets killed or gets terminated, the process activity mutates to a process result (state 2).

    A process result (state 2) contains information about how a process has terminated such as its
    exit status or exc_info if it has run a python function. This state is a mutation of a process
    activity object for which the represented process has finished executing.
    """

    def __new__(cls, *args, **kwargs):
        """
        Create and return a new Process object.
        """
        # extract keyword arguments:
        pid = kwargs.get('pid', 0)
        daemon = kwargs.get('daemon', False)
        state = kwargs.get('state', STATE_INITIALIZED)
        pipe_read = kwargs.get('pipe_read', 0)
        pipe_write = kwargs.get('pipe_write', 0)
        pipe_err = kwargs.get('pipe_err', 0)
        can_init = kwargs.get('_can_init', True)

        _type_check((pid, daemon, state, pipe_read, pipe_write, pipe_err, can_init), int, bool, int, int, int, int,
                    bool)

        __mcs = metaclassof(cls)  # fetch metaclass, which should be MultiMeta
        if __mcs != MultiMeta:
            raise TypeError("'Process.__new__' constructor was passed the wrong type as 'cls'.") from None

        # temporary variables:
        needs_init = (pid == 0) * (state == STATE_INITIALIZED) * can_init  # branch-less programming

        # create our instance and assign the right info slots
        self = super().__new__(cls)
        __mcs.set_info(self, 'id', pid)
        __mcs.set_info(self, 'needs_init', bool(needs_init))
        __mcs.set_info(self, 'running', not needs_init)
        __mcs.set_info(self, 'pipes', (pipe_read, pipe_write, pipe_err))
        __mcs.set_info(self, 'daemon', daemon)
        __mcs.set_info(self, 'state', state)
        __mcs.set_info(self, 'is_being_called', False)
        if (state == STATE_RUNNING) and MS_WINDOWS:
            __mcs.set_info(self, 'handle', _impl.open_process(pid))

        if state == STATE_RUNNING:
            _pthreads_info[pid] = {}

        return self

    def __init__(self, *args, **kwargs):
        """
        Initialize a Process object.
        """
        flags = kwargs.get('flags', 0)
        environ = kwargs.get('environ', {})
        curdir = kwargs.get('curdir', "")
        _type_check((flags, environ, curdir), int, dict, str)

        if len(args) not in (0, 1):
            raise TypeError(POS_ARGCOUNT_ERR_STR.format('Process.__init__()', '0 or 1', len(args))) from None

        __mcs = metaclassof(self)  # fetch the metaclass, which should be MultiMeta
        if __mcs != MultiMeta:
            raise TypeError(
                "'Process.__init__' constructor was passed an object of an invalid type as 'self'.") from None

        if not __mcs.get_info(self, 'needs_init'):  # object may already have been initialized
            return
        __mcs.set_info(self, 'needs_init', False)

        if len(args) > 0:
            _type_check((args[0],), (_types.FunctionType, str))

        target = args[0] if (len(args) == 1) and isinstance(args[0], _types.FunctionType) else NO_OP_PROCESS_TARGET
        command = args[0] if (len(args) == 1) and isinstance(args[0], str) else ''
        _type_check((target, command), _types.FunctionType, str)

        __mcs.set_info(self, 'target', target)
        __mcs.set_info(self, 'command', command)

        options = _impl.ProcessStartOptions()
        options.flags = flags
        options.curdir = curdir
        options.environ = environ
        options.close_fds = True

        if MS_WINDOWS:
            if (len(args) == 0) or isinstance(args[0], _types.FunctionType):
                show_window = kwargs.get('show_window', False)
                create_console = kwargs.get('create_console', False)
                _type_check((show_window, create_console), bool, bool)

                options.startupinfo = _impl.ProcessStartupInfo()
                options.show_window = show_window
                options.startupinfo.wShowWindow = (show_window * _impl.SW_SHOW) + ((not show_window) * _impl.SW_HIDE)
            elif isinstance(args[0], str):
                options.create_console = False

        elif isinstance(args[0], str):
            target = kwargs.get('target', NO_OP_PROCESS_TARGET)
            _type_check((target,), _types.FunctionType)
            options.preexec = target

        __mcs.set_info(self, 'options', options)

    def __dir__(self):
        """
        Implement dir(self)
        """
        result = []
        for attr in object.__dir__(self):
            if not attr.startswith('#'):
                result.append(attr)
        return result

    def __getstate__(self):
        """
        Helper for pickle.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Process.__getstate__() was passed an object of an invalid type as 'self'.") from None
        has_target = __mcs.has_info(self, 'target')

        res = {
            'id': __mcs.get_info(self, 'id'),
            'needs_init': __mcs.get_info(self, 'needs_init'),
            'running': __mcs.get_info(self, 'running'),
            'pipe_read': __mcs.get_info(self, 'pipes')[0],
            'pipe_write': __mcs.get_info(self, 'pipes')[1],
            'pipe_err': __mcs.get_info(self, 'pipes')[2],
            'daemon': __mcs.get_info(self, 'daemon'),
            'state': __mcs.get_info(self, 'state'),
            'command': __mcs.get_info(self, 'command') if __mcs.has_info(self, 'command') else None,
            'has_target': has_target,
            'stdin': __mcs.get_info(self, 'stdin') if __mcs.has_info(self, 'stdin') else None,
            'stdout': __mcs.get_info(self, 'stdout') if __mcs.has_info(self, 'stdout') else None,
            **pickle_function(None if not has_target else __mcs.get_info(self, 'target'), 'target'),
        }
        if MS_WINDOWS:
            res['handle'] = __mcs.get_info(self, 'handle') if __mcs.has_info(self, 'handle') else None
        return res

    def __setstate__(self, state):
        """
        Helper for pickle.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Process.__setstate__() was passed an object of an invalid type as 'self'.") from None

        has_target = state['has_target']
        if has_target:
            _target = unpickle_function(state, 'target')
            __mcs.set_info(self, 'target', _target)

        _pid = state['id']
        _needs_init = state['needs_init']
        _running = state['running']
        _pipes = state['pipe_read'], state['pipe_write'], state['pipe_err']
        _daemon = state['daemon']
        _state = state['state']
        _command = state['command']
        _stdin = state['stdin']
        _stdout = state['stdout']
        _handle = state['handle']

        __mcs.set_info(self, 'id', _pid)
        __mcs.set_info(self, 'needs_init', _needs_init)
        __mcs.set_info(self, 'running', _running)
        __mcs.set_info(self, 'pipes', _pipes)
        __mcs.set_info(self, 'daemon', _daemon)
        __mcs.set_info(self, 'state', _state)

        if _command is not None:
            __mcs.set_info(self, 'command', _command)
        if _stdin is not None:
            __mcs.set_info(self, 'stdin', _stdin)
        if _stdout is not None:
            __mcs.set_info(self, 'stdout', _stdout)
        if _handle is not None:
            __mcs.set_info(self, 'handle', _handle)

    def __mul__(self, other):
        """
        Implement self * other for cases where other is 0 or 1.
        """
        match other:
            case 1:
                return self
            case 0:
                return 0
            case _:
                raise TypeError(f"Unsupported operand values {repr(self)}, {repr(other)} for *.") from None

    def __call__(self, *args, **kwargs):
        """
        __call__(self, *args, **kwargs) -> Process
        Start a new process from a process model and return the process activity associated with the
        new process.
        """
        timeout = 5000  # thread / process calling timeout in milliseconds

        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Process.__call__() was passed an object of an invalid type as 'self'.") from None

        if self.state != STATE_INITIALIZED:
            raise ProcessStateError("Only process models can be called.") from None

        start_time = time.time()
        while __mcs.get_info(self, 'is_being_called') * ((time.time() - start_time) < (timeout / 1000)):
            pass
        if time.time() - start_time > timeout / 1000:
            return  # timeout expired

        __mcs.set_info(self, 'is_being_called', True)

        proc = __mcs.copy(self)

        if __mcs.get_info(proc, 'command') == "":  # process was not required to be a command
            p2c, c2p, err, exc_info_pipe = _impl.create_new_pipe(), _impl.create_new_pipe(), _impl.create_new_pipe(), _impl.create_new_pipe()

            options = __mcs.get_info(proc, 'options')
            options.p2c = p2c
            options.c2p = c2p
            options.err = err
            options.exc_info_pipe = exc_info_pipe
            __mcs.set_info(proc, 'options', options)
            proc_code = _build_proc_code((p2c[0], c2p[1], err[1], exc_info_pipe[1]), pickle.dumps(proc), args, kwargs)
            # print('<code>', proc_code, '</code>')
            command = f"\"{sys.executable}\" -c \"{proc_code}\""
            proc_info, th_info, pipes = _impl.start_new_process(command, __mcs.get_info(proc, 'options'))

            if not __mcs.get_info(proc, 'daemon'):
                _blocking_processes[proc_info[0]] = proc

        else:
            shell = kwargs.get('shell', False)
            _type_check((shell,), bool)

            options = __mcs.get_info(proc, 'options')
            if shell:
                proc_info, th_info, pipes = _impl.execute_command(__mcs.get_info(proc, 'command'), options,
                                                                  curdir=options.curdir)
            else:
                proc_info, th_info, pipes = _impl.start_new_process(__mcs.get_info(proc, 'command'), options)

            _blocking_processes[proc_info[0]] = proc

        if MS_WINDOWS:
            __mcs.set_info(proc, 'handle', proc_info[1])

        __mcs.set_info(proc, 'id', proc_info[0])

        __mcs.set_info(proc, 'stdin', proc_info[2][0])
        __mcs.set_info(proc, 'stdout', proc_info[2][1])
        __mcs.set_info(proc, 'pipes', pipes)

        __mcs.set_info(proc, 'state', STATE_RUNNING)

        th = _thread.Thread.__new__(_thread.Thread, proc,
                                    th_info[0])  # using our special constructor to open an existing thread
        _pthreads_info[proc.pid] = {}
        _pthreads_info[proc.pid][th_info[0]] = th

        __mcs.set_info(proc, 'is_being_called', False)
        __mcs.set_info(self, 'is_being_called', False)
        print(pipes)

        """  ## code sample that transmits the process' stderr to the current stderr ## 
        for i in range(1000):
            try:
                print(str(_winapi.ReadFile(pipes[2], 100)[0], encoding=DEFAULT_ENCODING).replace('\n', ''),
                      file=sys.stderr)
            except BrokenPipeError:
                break"""

        return proc

    def __repr__(self):
        """
        Implement repr(self)
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Process.__repr__() was passed an object of an invalid type as 'self'.") from None

        if __mcs.get_info(self, 'state') == STATE_INITIALIZED:
            model_name = f" at {hex(id(self))}" if __mcs.get_info(self, 'target') == NO_OP_PROCESS_TARGET \
                else f" '{__mcs.get_info(self, 'target').__name__}'"
            return f"<process model{model_name}>"
        return f"<process at {hex(id(self))}, pid={__mcs.get_info(self, 'id')}>"

    @classmethod
    def __open__(cls, pid):
        """
        Open an already running process and return a process activity associated with it.
        Trying to open the 'System Idle Process' process (pid of 0) or 'System' process (pid
        of 4) will raise PermissionError.
        """
        _type_check((pid,), int)
        if pid in (0, 4):
            raise PermissionError("Access denied.")

        _daemon = True  # (pid != _impl.get_current_process())
        return cls.__new__(cls, pid=pid, daemon=_daemon, state=STATE_RUNNING, _can_init=False)

    def terminate(self):
        """
        Terminate a process.
        If process is the current process, exit interpreter with code -1.
        Return whether this function succeeded.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Process.__repr__() was passed an object of an invalid type as 'self'.") from None

        if self.state == STATE_TERMINATED:
            return True
        elif self.state == STATE_INITIALIZED:
            raise ProcessStateError("Process models have no attribute 'terminate'.") from None

        if __mcs.get_info(self,
                          'id') == _impl.get_current_process():  # exit the interpreter if the current process is terminated.
            raise SystemExit(-1) from None

        if MS_WINDOWS:
            res = _impl.terminate_process(__mcs.get_info(self, 'handle'), handle=True)
        else:
            res = _impl.terminate_process(__mcs.get_info(self, 'id'))

        if res and (__mcs.get_info(self, 'id') in _pthreads_info):
            del _pthreads_info[__mcs.get_info(self, 'id')]

        return res

    def kill(self):
        """
        Kill a process.
        If process is the current process, exit interpreter with code -1.
        Return whether this function succeeded.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("Process.__repr__() was passed an object of an invalid type as 'self'.") from None

        if self.state == STATE_TERMINATED:
            return True
        elif self.state == STATE_INITIALIZED:
            raise ProcessStateError("Process models have no attribute 'kill'.") from None

        if __mcs.get_info(self,
                          'id') == _impl.get_current_process():  # exit the interpreter if the current process is terminated.
            raise SystemExit(-1) from None

        if MS_WINDOWS:
            res = _impl.kill_process(__mcs.get_info(self, 'handle'), handle=True)
        else:
            res = _impl.kill_process(__mcs.get_info(self, 'id'))

        if res and (__mcs.get_info(self, 'id') in _pthreads_info):
            del _pthreads_info[__mcs.get_info(self, 'id')]

        return res

    def exc_info(self):
        """
        Return exception information for the process as returned by sys.exc_info().
        If the process is not known to run python code, or has not been created
        locally, this will always return (None, None, None).
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("'Process.exc_info()' was passed an object of an invalid type as 'self'.") from None

        if self.state == STATE_INITIALIZED:
            raise ProcessStateError("Process models have no attribute 'exc_info'.")

        if self.state != STATE_TERMINATED:
            return None, None
        exc_info_partial = _impl.get_proc_exc_info(__mcs.get_info(self, 'pipes')[3])
        if exc_info_partial == (None, None):
            return None, None, None
        if exc_info_partial is None:
            return None
        try:
            raise Exception
        except:
            etb = sys.exc_info()[2]
        return *exc_info_partial, etb

    def get_thread(self, tid):
        _type_check((tid,), int)
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("'Process.get_thread()' was passed an object of an invalid type as 'self'.") from None
        if self.pid not in _pthreads_info:
            raise ValueError(f"Process {self.pid} has finished executing.")

        threads = _pthreads_info[self.pid]
        if tid in threads:
            return threads[tid]
        raise ValueError(f"Process {self.pid} owns no thread of id {tid}.")

    @classmethod
    def get_current_process(cls):
        """
        Return a process activity representing the current process.
        """
        return cls.__open__(_impl.get_current_process())

    @property
    def exit_status(self):
        """
        Exit status of the process.
        Will be None if the process is still running.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("'Process.exit_status.fget()' was passed an object of an invalid type as 'self'.") from None

        state = __mcs.get_info(self, 'state')
        if state == STATE_INITIALIZED:
            raise ProcessStateError("Process models have no attribute 'exit_status'.") from None

        if __mcs.get_info(self, 'state') == STATE_INITIALIZED:
            raise ProcessStateError("Process models don't have an exit status.")

        if MS_WINDOWS:
            try:
                status = _impl.get_process_exit_code(__mcs.get_info(self, 'handle'), handle=True)
            except ProcessLookupError:
                return None
        else:
            status = _impl.get_process_exit_code(__mcs.get_info(self, 'id'))

        if status == _impl.STILL_ACTIVE:
            return
        return status

    @property
    def state(self):
        """
        The current state of a Process object.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("'Process.state.fget()' was passed an object of an invalid type as 'self'.") from None

        _state = __mcs.get_info(self, 'state')
        try:
            if self.exit_status is None:
                return _state
        except ProcessStateError:
            return _state
        return STATE_TERMINATED

    @property
    def known_threads(self):
        """
        A tuple of all known threads for this process.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError(
                "'Process.known_threads.fget()' was passed an object of an invalid type as 'self'.") from None

        if __mcs.get_info(self, 'id') not in _pthreads_info:
            return ()

        return tuple((th for th in _pthreads_info[__mcs.get_info(self, 'id')].values()))

    @property
    def stdin(self):
        """
        Return the process' standard input stream.
        Read-only from inside the process, write-only from outside the process.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("'Process.stdin.fget()' was passed an object of an invalid type as 'self'.") from None

        if self.pid == _impl.get_current_process():
            return _io.Stream(sys.stdin)

        stdin = __mcs.get_info(self, 'pipes')[0]
        return _io.Stream(stdin, readable=False, writable=True, name=f'<{self.pid}:stdin>')

    @property
    def stdout(self):
        """
        Return the process' standard output stream.
        Write-only from inside the process, read-only from outside the process.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("'Process.stdout.fget()' was passed an object of an invalid type as 'self'.") from None

        if self.pid == _impl.get_current_process():
            return _io.Stream(sys.stdout)

        stdout = __mcs.get_info(self, 'pipes')[1]
        return _io.Stream(stdout, readable=True, writable=False, name=f'<{self.pid}:stdout>')

    @property
    def stderr(self):
        """
        Return the process' standard error stream.
        Write-only from inside the process, read-only from outside the process.
        """
        __mcs = metaclassof(self)
        if __mcs != MultiMeta:
            raise TypeError("'Process.stdout.fget()' was passed an object of an invalid type as 'self'.") from None

        if self.pid == _impl.get_current_process():
            return _io.Stream(sys.stderr)

        stderr = __mcs.get_info(self, 'pipes')[2]
        return _io.Stream(stderr, readable=True, writable=False, name=f'<{self.pid}:stderr>')

    pid = property(lambda self: MultiMeta.get_info(self, 'id'))
    """The process id of the process. This is zero for process models."""


def __finalize__():
    """
    Wait for all non-daemon processes to terminate.
    """
    for pid, process in _blocking_processes.items():
        while process.state == STATE_RUNNING:  # wait for the process to terminate
            pass
