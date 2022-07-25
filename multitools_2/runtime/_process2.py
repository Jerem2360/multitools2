import _thread
import os
import sys

from .._meta import MultiMeta
from .._errors import *
from .._typing import *
from .._builtindefs import *
from ._shared_memory import SharedDict
from .._const import *
from .._helpers import *
from ._database import _all_processes, _all_python_processes, _current_proc_threads, \
    DataBaseElement, NUL_HVal
from .. import io

if MS_WINDOWS:
    from .._win32 import pipe as _pipe, getpid as _getpid, close as _close, process as _process, \
        terminate as _terminate, kill as _kill, join as _join, exit_status as _e_status
    from .._win32 import raw_stdin as _raw_stdin, raw_stdout as _raw_stdout, raw_stderr as _raw_stderr
    from .. import _win32
else:
    from os import pipe as _pipe, getpid as _getpid, close as _close
    from .._posix import process as _process, terminate as _terminate, kill as _kill, join as _join, \
        exit_status as _e_status
    from .._posix import raw_stdin as _raw_stdin, raw_stdout as _raw_stdout, raw_stderr as _raw_stderr


"""
## ------ old attributes ------ ##

infos:
- id
- needs_init
- running
- pipes
- daemon
- state
- is_being_called
if MS_WINDOWS - handle
- target
- command
- options
- stdin
- stdout
properties:
- pid
- exit_status
- state
- known_threads
- stdin
- stdout
- stderr
methods:
- static get_current_process()
- get_thread(id)
- exc_info()
- kill()
- terminate()
- static __open__(pid)


## ------ new attributes ------ ##

=> PROC_OPENED:
infos:
- id
- needs_init = False
- daemon = True
- properties: (STATE_RUNNING -> STATE_TERMINATED, PROC_OPENED)
- is_being_called = False
- handle if MS_WINDOWS
=> PROC_CREATED_FUNCTION
- id if state >= STATE_RUNNING
- needs_init
- pipes (stdin, stdout, stderr, exc_info)
- daemon
- properties: (STATE_INITIALIZED -> STATE_RUNNING -> STATE_TERMINATED, PROC_CREATED_FUNCTION)
- is_being_called
- handle if MS_WINDOWS
- target
- options

=> PROC_CREATED_COMMAND
infos:
- id if state >= STATE_RUNNING
- needs_init
- pipes (stdin, stdout, stderr)
- daemon
- properties: (STATE_INITIALIZED -> STATE_RUNNING -> STATE_TERMINATED, PROC_CREATED_COMMAND)
- is_being_called
- handle if MS_WINDOWS
- command
- options
specific implementations:
- exc_info() => None
- threads => [only the process' main thread]

=> PROC_CURRENT
infos:
- id
- needs_init = False
- daemon = False
- properties: (STATE_RUNNING, PROC_MAIN)
specific implementations:
- kill(), terminate() => sys.exit(-1)
- join => ProcessError("A process cannot join itself.")
- exit_status => None
- exc_info() => sys.exc_info()
- state => state_running
- stdin, stdout, stderr => sys.stdin, sys.stdout, sys.stderr


=> Methods

static open(pid)
static get_current_process() => _CurrentProcess
kill()
terminate()
exc_info()
join()

=> Properties

threads
state
exit_status
stdin
stdout
stderr


runtime infos:
- lid
- state
- tp

model infos:
- command or target
- state
- tp
- options



"""

_blocking_processes = {}
# e.g.  {'tp': 0, 'state': 0, 'id': 0, 'run': b'', 'exit_status': None}


"""
To figure in the launched processes' code:

os.environ['{MAIN_PROC_ENV_NAME}'] = '{MAIN_PROCESS_ID}'
os.environ['{ENV_PROCS}'] = '{_all_processes.name}'
os.environ['{ENV_PY_PROCS}'] = '{_all_python_processes.name}'

"""


# process object types:
PROC_OPENED = 0
PROC_CREATED_FUNCTION = 1
PROC_CREATED_COMMAND = 2
PROC_CURRENT = 3


class ProcessOptions:
    def __init__(self, **options):
        for name, value in options.items():
            setattr(self, name, value)

    def get_option(self, name, *args, **kwargs):
        has_default = False
        if len(args) == 1:
            default = args[0]
            has_default = True
        elif 'default' in kwargs:
            default = kwargs['default']
            has_default = True

        try:
            return getattr(self, name)
        except AttributeError as e:
            if not has_default:
                raise e from None
            # noinspection PyUnboundLocalVariable
            return default


def _current_proc_target(proc, *args, **kwargs):
    """
    A function representing the current process's activity.
    When called, it requires the process to be passed in as
    first argument, and returns 0 upon success, -1 upon user
    interruption and SystemExit.code upon SystemExit
    (e.g. sys.exit(code), exit()).

    Keep in mind that this should not be used except if you are
    absolutely sure that you have no alternative, since this is pretty much
    unsafe and could lead to undefined behaviour.

    PS: if the function tries to exit the interpreter, it will simply
    return -1 instead. This is done so that the main program doesn't exit
    for no apparent reason.
    """
    import __main__
    # noinspection PyTypeChecker
    main_code = compile(__main__, __main__.__file__, 'exec')
    try:
        exec(main_code, globals())
    except SystemExit as s:
        return s.code
    except KeyboardInterrupt:
        return -1
    except:
        raise
    return 0


class Process(metaclass=MultiMeta):
    def __new__(cls, *args, **kwargs):
        """
        Process(pid) -> Process {PROC_OPENED}
        Process(target, **options) -> Process {PROC_CREATED_FUNCTION}
        Process() -> Process {PROC_CURRENT}
        Process(command, **options) -> Process {PROC_CREATED_COMMAND}
        """
        self = super().__new__(cls)
        if MS_WINDOWS:
            self = MultiMeta.set_info(self, 'handle', 0)
        self = MultiMeta.set_info(self, 'initialized', False)  # each instance must be initialized exactly once.
        self = MultiMeta.set_info(self, 'db_elem', None)
        self = MultiMeta.set_info(self, 'state', 0)
        self = MultiMeta.set_info(self, 'is_called', False)

        return self

    def __init__(self, *args, **kwargs):

        if MultiMeta.get_info(self, 'initialized'):  # each instance must be initialized exactly once.
            return

        match len(args):
            case 0:
                pid = _getpid()
                state = STATE_RUNNING
                tp = PROC_CURRENT
                run = _current_proc_target
                if MS_WINDOWS:
                    handle = _win32.open_process(pid)

            case 1:
                if isinstance(args[0], int):
                    pid = args[0]
                    state = STATE_RUNNING
                    tp = PROC_OPENED
                    run = None
                    if MS_WINDOWS:
                        handle = _win32.open_process(pid)
                elif isinstance(args[0], (Function, Method)):
                    pid = 0
                    state = STATE_INITIALIZED
                    tp = PROC_CREATED_FUNCTION
                    run = args[0]
                    if MS_WINDOWS:
                        handle = 0

                elif isinstance(args[0], str):
                    pid = 0
                    state = STATE_INITIALIZED
                    tp = PROC_CREATED_COMMAND
                    run = args[0]
                    if MS_WINDOWS:
                        handle = 0

                else:
                    raise TypeError(TYPE_ERR_STR.format('int | function | str', type(args[0]).__name__))

            case _:
                raise TypeError(POS_ARGCOUNT_ERR_STR.format('Process.__init__()', '0 or 1', len(args)))

        if tp in (PROC_OPENED, PROC_CURRENT):  # user wants to open a process
            db_elem = DataBaseElement.find(_all_processes, id=pid, state=STATE_RUNNING)

            if db_elem is None:
                db_elem = DataBaseElement.create(_all_processes)

            if 'tp' not in db_elem:
                db_elem['tp'] = tp

            if 'pipes' not in db_elem:
                db_elem['pipes'] = (None, None, None)

            if 'known_threads' not in db_elem:
                db_elem['known_threads'] = (_thread.get_native_id(),) if tp == PROC_CURRENT else ()

            if 'id' not in db_elem:
                db_elem['id'] = pid

            if 'state' not in db_elem:
                db_elem['state'] = state

            # print(db_elem)

            MultiMeta.set_info(self, 'state', STATE_RUNNING)

            MultiMeta.set_info(self, 'db_elem', db_elem)
            if MS_WINDOWS:
                # noinspection PyUnboundLocalVariable
                MultiMeta.set_info(self, 'handle', handle)

        else:  # user wants to create a process model
            daemon = kwargs.get('daemon', True)
            type_check((daemon,), bool)
            MultiMeta.set_info(self, 'daemon', daemon)
            MultiMeta.set_info(self, 'state', state)
            if tp == PROC_CREATED_FUNCTION:
                MultiMeta.set_info(self, 'target', run)
            else:
                MultiMeta.set_info(self, 'command', run)

            options = {
                'flags': kwargs.get('flags', 0),
                'curdir': kwargs.get('curdir', ""),
                'environ': kwargs.get('environ', {})
            }
            type_check((options['flags'], options['curdir'], options['environ']), int, str, dict)
            MultiMeta.set_info(self, 'options', ProcessOptions(**options))

        MultiMeta.set_info(self, 'tp', tp)

        if tp == PROC_CREATED_FUNCTION:
            self.__annotations__ = run.__annotations__
            self.__closure__ = run.__closure__
            self.__code__ = run.__code__
            self.__defaults__ = run.__defaults__
            self.__kwdefaults__ = run.__kwdefaults__
            self.__module__ = run.__module__
            self.__name__ = run.__name__
            self.__qualname__ = run.__qualname__
            self.__doc__ = run.__doc__

        MultiMeta.set_info(self, 'initialized', True)

    def __getstate__(self):
        tp = MultiMeta.get_info(self, 'tp')
        if tp == PROC_CURRENT:
            tp = PROC_OPENED

        if MultiMeta.has_info(self, 'target'):
            run = MultiMeta.get_info(self, 'target')
        elif MultiMeta.has_info(self, 'command'):
            run = MultiMeta.get_info(self, 'command')
        else:
            run = None

        return {
            'lid': MultiMeta.get_info(self, 'db_elem').id if MultiMeta.get_info(self, 'db_elem') is not None else None,
            'tp': tp,
            'run': run if tp == PROC_CREATED_COMMAND or run is None else pickle_function2(run),
            'state': MultiMeta.get_info(self, 'state') if MultiMeta.get_info(self, 'state') is not None else None,
            'id': self.pid if 'id' in MultiMeta.get_info(self, 'db_elem') else None,
            'options': MultiMeta.get_info(self, 'options') if MultiMeta.has_info(self, 'options') else None,
            'daemon': MultiMeta.get_info(self, 'daemon') if MultiMeta.has_info(self, 'daemon') else None,
            'initialized': MultiMeta.get_info(self, 'initialized')
        }

    def __setstate__(self, state):
        if not state['initialized']:
            return
        local_id = state['lid']
        MultiMeta.set_info(self, 'initialized', True)
        if local_id is None:  # case of a process model
            MultiMeta.set_info(self, 'state', STATE_INITIALIZED)
            run = state['run']
            if isinstance(run, str):
                MultiMeta.set_info(self, 'command', run)
                tp = PROC_CREATED_COMMAND

            else:
                MultiMeta.set_info(self, 'target', unpickle_function2(run))
                tp = PROC_CREATED_FUNCTION

            MultiMeta.set_info(self, 'tp', tp)
            MultiMeta.set_info(self, 'options', state['options'])
            return

        if local_id in _all_processes:
            db_elem = DataBaseElement(_all_processes, local_id)

            proc_id = db_elem['id'] if 'id' in db_elem else state['id']
            if MS_WINDOWS:
                MultiMeta.set_info(self, 'handle', _win32.open_process(proc_id))

            MultiMeta.set_info(self, 'state', STATE_RUNNING)
            if self._get_exit_status() is None:
                proc_state = STATE_RUNNING
            else:
                proc_state = STATE_TERMINATED

            MultiMeta.set_info(self, 'state', proc_state)

            if 'id' not in db_elem:
                db_elem['id'] = state['id']

            db_elem['state'] = proc_state

            tp = PROC_CURRENT if db_elem['id'] == _getpid() else PROC_OPENED

        else:
            db_elem = DataBaseElement.create(_all_processes)
            if MS_WINDOWS:
                MultiMeta.set_info(self, 'handle', -1)

            MultiMeta.set_info(self, 'state', STATE_TERMINATED)
            db_elem['state'] = STATE_TERMINATED
            db_elem['id'] = state['id']
            tp = PROC_OPENED

        if state['run'] is not None:
            run = state['run']
            if isinstance(run, str):
                MultiMeta.set_info(self, 'command', run)
                tp = PROC_CREATED_COMMAND

            else:
                MultiMeta.set_info(self, 'target', unpickle_function2(run))
                tp = PROC_CREATED_FUNCTION

        MultiMeta.set_info(self, 'db_elem', db_elem)
        MultiMeta.set_info(self, 'tp', tp)

    def __call__(self, *args, **kwargs):

        if self._get_state() != STATE_INITIALIZED:
            raise ProcessStateError("Only process models are callable.")

        while True:
            # multiple threads / processes may not call the same instance simultaneously,
            # so wait for our turn to do so
            if not MultiMeta.get_info(self, 'is_called'):
                break

        MultiMeta.set_info(self, 'is_called', True)

        proc: Process = MultiMeta.copy(self)

        proc_read, proc_write, proc_err, proc_exc_info = _pipe(), _pipe(), _pipe(), _pipe()
        options = MultiMeta.get_info(proc, 'options')

        db_elem = DataBaseElement.create(_all_processes)
        db_elem['state'] = STATE_RUNNING

        MultiMeta.set_info(proc, 'db_elem', db_elem)

        MultiMeta.set_info(proc, 'state', STATE_RUNNING)

        if MultiMeta.get_info(proc, 'tp') == PROC_CREATED_FUNCTION:
            options.p2c = proc_read
            options.c2p = proc_write
            options.err = proc_err
            options.exc_info_pipe = proc_exc_info

            code = proc._build_code((proc_read[0], proc_write[1], proc_err[1], proc_exc_info[1]), args, kwargs)
            command = f"\"{sys.executable}\" -c \"{code}\""
            proc_info, th_info, pipes = _process(command, options)

            if not MultiMeta.get_info(proc, 'daemon'):
                _blocking_processes[proc_info[0]] = proc

            py = True
            run = pickle_function2(MultiMeta.get_info(proc, 'target'))

        else:
            shell = options.get_option('shell', False)
            create_window = options.get_option('create_window', False)
            type_check((shell, create_window), bool, bool)

            use_std_handles = not create_window

            if use_std_handles:  # use current standard streams if we don't need to create a window
                options.p2c = _raw_stdin if not hasattr(options, 'p2c') else options.p2c
                options.c2p = _raw_stdout if not hasattr(options, 'c2p') else options.c2p
                options.err = _raw_stderr if not hasattr(options, 'err') else options.err

            if shell:
                command = f"{SHELL} {SHELL_OPT}c \"{MultiMeta.get_info(proc, 'command')}\""
            else:
                command = MultiMeta.get_info(proc, 'command')

            proc_info, th_info, pipes = _process(command, options)

            _blocking_processes[proc_info[0]] = proc

            py = False
            run = MultiMeta.get_info(proc, 'command')

        if MS_WINDOWS:
            MultiMeta.set_info(proc, 'handle', proc_info[1])

        if py:
            _all_python_processes[db_elem.id] = None

        db_elem['id'] = proc_info[0]
        db_elem['tp'] = MultiMeta.get_info(proc, 'tp')
        db_elem['run'] = run
        db_elem['pipes'] = pipes

        MultiMeta.set_info(proc, 'db_elem', db_elem)

        if not MultiMeta.get_info(proc, 'daemon', True):
            _blocking_processes[proc.pid] = proc

        known_threads = (th_info[0],)
        db_elem['known_threads'] = known_threads

        MultiMeta.set_info(self, 'is_called', False)
        MultiMeta.set_info(proc, 'is_called', False)

        return proc

    def __repr__(self):
        tp = MultiMeta.get_info(self, 'tp')
        state = self._get_state()
        if state == STATE_INITIALIZED:
            if tp == PROC_CREATED_FUNCTION:
                return f"<process model '{MultiMeta.get_info(self, 'target').__qualname__}'>"
            return f"<process model at {hex(id(self))}, command='{MultiMeta.get_info(self, 'command')}'>"
        if state == STATE_RUNNING:
            return f"<activity of process {self.pid}>"
        return f"<terminated process {self.pid}>"

    def __del__(self):
        if MS_WINDOWS:  # on Windows, the handle to the underlying process should be closed
            try:
                _close(MultiMeta.get_info(self, 'handle'))
            except:
                pass

    def _get_state(self):
        if MultiMeta.get_info(self, 'db_elem') is not None:
            db_elem = MultiMeta.get_info(self, 'db_elem')
            if 'state' not in db_elem:
                return STATE_RUNNING
            # state = db_elem['state']
            true_state = STATE_RUNNING if self.exit_status is None else STATE_TERMINATED
            if db_elem['state'] != true_state:
                db_elem['state'] = true_state
            return db_elem['state']

        if MultiMeta.has_info(self, 'state'):
            return MultiMeta.get_info(self, 'state')
        return STATE_TERMINATED

    def _get_type(self):
        if self.pid == _getpid():
            return PROC_CURRENT
        return MultiMeta.get_info(self, 'db_elem')['tp']

    def _get_threads(self):
        if MS_WINDOWS:
            return _win32.enum_proc_threads(self.pid)
        db_elem = MultiMeta.get_info(self, 'db_elem')
        return list(db_elem['known_threads'])

    def _get_id(self):
        db_elem = MultiMeta.get_info(self, 'db_elem')
        return db_elem['id']

    def _get_exit_status(self, id_=None):
        if MS_WINDOWS:
            handle = MultiMeta.get_info(self, 'handle')
            if handle == 0:
                raise ProcessStateError('Process models have no exit status. (handle was 0)')
            if handle == -1:
                return 0
            return _e_status(handle)
        if MultiMeta.get_info(self, 'state') == STATE_INITIALIZED:
            raise ProcessStateError('Process models have no exit status.')
        if id_ is None:
            id_ = self._get_id()
        return _e_status(id_)

    def _build_code(self, pipes, call_args, call_kwargs):
        """
        Build the code that a process should execute at runtime.
        """
        try:
            p_args = pickle.dumps(call_args)
        except pickle.PicklingError:
            raise ValueError('Arguments must be pickleable.') from None
        args_code_snip = self._split_bytes_lines_for_code(p_args)

        try:
            p_kwargs = pickle.dumps(call_kwargs)
        except pickle.PicklingError:
            raise ValueError('Arguments must be pickleable.') from None
        kwargs_code_snip = self._split_bytes_lines_for_code(p_kwargs)

        p_proc = pickle.dumps(self)
        proc_code_snip = self._split_bytes_lines_for_code(p_proc)

        """
        When an existing process spawns a new one (only if its activity is a python function),
        the former passes various important information to the latter, such as the id of the 
        main process (i.e. the process at the top of the current hierarchy) or the names of
        shared memory blocks that the latter should share with the former and all the other 
        processes of the hierarchy.        
        """

        return f"""
import sys, time, io, pickle, os
os.environ['{MAIN_PROC_ENV_NAME}'] = '{MAIN_PROCESS_ID}'  # set the main process id to that of the parent process
os.environ['{ENV_PROCS}'] = '{_all_processes.name}'  # pass in shared memory names
os.environ['{ENV_PY_PROCS}'] = '{_all_python_processes.name}'


_MS_WINDOWS = sys.platform == 'win32'
if _MS_WINDOWS:
    import _winapi

in_, out, err, e_info = ({int(pipes[0])}, {int(pipes[1])}, {int(pipes[2])}, {int(pipes[3])})  # pass in the process' pipes
time.sleep(0.1)


try:
    # pass in and unpickle the process object:
    proc_b = {proc_code_snip}
    f = io.BytesIO(proc_b)
    proc = pickle.Unpickler(f).load()
except:
    sys.excepthook(*sys.exc_info())
    raise SystemExit(101)

# pass in and unpickle the args:
args_b = {args_code_snip}
args = pickle.loads(args_b)

# pass in and unpickle the kwargs:
kwargs_b = {kwargs_code_snip}
kwargs = pickle.loads(kwargs_b)

# get the function that the process should be running:
print(proc.__dict__)
func = getattr(proc, '#target')
try:
    # call it given args and kwargs:
    exit_code = func(proc, *args, **kwargs)
except SystemExit as e:
    # if python is required to exit, ignore SystemExit and set our code accordingly:
    exit_code = e.code
except KeyboardInterrupt:
    # if the user interrupted the process it will exit with code -1.
    exit_code = -1
except:
    # if an exception occurred, print it to sys.stderr and set exit code to 1:
    sys.excepthook(*sys.exc_info())
    exit_code = 1

type(proc).get_current_process()._del_from_pyprocs()  # remove the current process from the list

# exit interpreter with the given code:
if not isinstance(exit_code, int):
    exit_code = 0
    if hasattr(exit_code, '__bool__'):
        exit_code = int(bool(exit_code))
raise SystemExit(exit_code) from None
"""

    @staticmethod
    def _split_bytes_lines_for_code(data):
        all_data = repr(data)
        b_size = len(all_data)
        b_setter = "b'"
        lines_count = int(b_size / 2000) + 1  # round to higher int value
        start = 0
        end = 2000
        for i in range(lines_count):
            data = all_data[start:end]
            last_bytes = data[-3:]
            if '\\' in last_bytes:  # check for escape codes
                mov_amount = 3 - last_bytes.find('\\')
                end -= mov_amount
                data = all_data[start:end]

            po = data.removeprefix("b'").removesuffix("'")
            b_setter += po
            b_setter += "' \\\n    + b'"

            start = end
            end += 2000
        b_setter = b_setter.removesuffix(" \\\n    + b'")

        return b_setter

    def _get_pipes(self):
        return MultiMeta.get_info(self, 'db_elem')['pipes']

    def _check_started(self, msg):
        if self._get_state() == STATE_INITIALIZED:
            raise ProcessStateError(msg)

    def _del_from_pyprocs(self):
        MultiMeta.get_info(self, 'db_elem').remove()

    def terminate(self):
        """
        Terminate the process.
        Terminating the current process is equivalent to exiting the interpreter.
        """
        self._check_started('Cannot terminate a process model.')
        if self.pid == _getpid():
            raise SystemExit(-1)
        if MS_WINDOWS:
            return _terminate(MultiMeta.get_info(self, 'handle'))
        return _terminate(self.pid)

    def kill(self):
        """
        Kill the process.
        Killing the current process is equivalent to exiting the interpreter.
        """
        self._check_started('Cannot kill a process model.')
        if self.pid == _getpid():
            raise SystemExit(-1)
        if MS_WINDOWS:
            return _kill(MultiMeta.get_info(self, 'handle'))
        return _kill(self.pid)

    def join(self, timeout=None):
        """
        Wait for the process to terminate.

        On windows, timeout fixes the maximum amount of time to wait, in seconds.
        On posix systems, timeout is ignored.
        """
        self._check_started('Cannot join a process model.')
        if self._get_state() == STATE_TERMINATED:
            return
        if self.pid == _getpid():
            raise ProcessError('A process cannot join itself.')
        if MS_WINDOWS:
            if timeout is not None:
                timeout = timeout * 1000
            _join(MultiMeta.get_info(self, 'handle'), timeout)
            return self.exit_status

        return _join(self.pid)

    @classmethod
    def open(cls, pid):
        """
        Open an existing process, given its pid.
        """
        type_check(pid, int)
        return cls(pid)

    @classmethod
    def get_current_process(cls):
        """
        Return the activity of the current process.
        The current process cannot be joint.
        Attempting to terminate or kill it will
        exit the interpreter.
        """
        return _CurrentProcess

    @property
    def exit_status(self):
        """
        The exit status of the current process.
        This is None if the process has not yet terminated.
        """
        if MultiMeta.get_info(self, 'state') == STATE_INITIALIZED:
            raise ProcessStateError('Process models don\'t have an exit status.')
        if MS_WINDOWS:
            # print('handle:', MultiMeta.get_info(self, 'handle'))
            return _e_status(MultiMeta.get_info(self, 'handle'))
        return _e_status(self.pid)

    @property
    def state(self):
        """
        The current state of the process, i.e. RUNNING or TERMINATED.
        This is INITIALIZED for process models.
        """
        return self._get_state()

    @property
    def pid(self):
        """
        The pid of the process.
        This is zero for process models.
        """
        if self._get_state() == STATE_INITIALIZED:
            return 0
        # print(_all_processes)
        return MultiMeta.get_info(self, 'db_elem')['id']

    @property
    def stdin(self):
        """
        The process' standard input stream.
        When self is the current process, this corresponds to sys.stdin.

        Note: This property's result is a:
        - read-only stream if self is the current process
        - write-only stream otherwise.
        """
        self._check_started('Process models have no standard input stream.')
        if self.pid == _getpid():
            return io.Stream(sys.stdin)
        pipe = self._get_pipes()[0]
        return io.Stream(pipe, readable=False, writable=True)

    @property
    def stdout(self):
        """
        The process' standard output stream.
        When self is the current process, this corresponds to sys.stdout.

        Note: This property's result is a:
        - write-only stream if self is the current process
        - read-only stream otherwise.
        """
        self._check_started('Process models have no standard output stream.')
        if self.pid == _getpid():
            return io.Stream(sys.stdout)
        pipe = self._get_pipes()[1]
        return io.Stream(pipe, readable=True, writable=False)

    @property
    def stderr(self):
        """
        The process' standard error stream.
        When self is the current process, this corresponds to sys.stderr.

        Note: This property's result is a:
        - write-only stream if self is the current process
        - read-only stream otherwise.
        """
        self._check_started('Process models have no standard error stream.')
        if self.pid == _getpid():
            return io.Stream(sys.stderr)
        pipe = self._get_pipes()[2]
        return io.Stream(pipe, readable=True, writable=False)

    @property
    def threads(self):
        """
        A list of the currently known threads of this process.
        On Windows, this lists exactly all threads that are currently running on
        this process.
        On posix, this lists only the threads the library knows about, lacking a system call for this.
        Return an empty iterable for process models and processes that have already terminated.
        """
        if self._get_state() in (STATE_INITIALIZED, STATE_TERMINATED):
            return ()
        from . import _thread2
        return tuple((_thread2.Thread.__open__(t) for t in self._get_threads()))


def __finalize__():
    for pid, proc in _blocking_processes:
        try:
            proc.join()
        except ProcessError:
            pass

    _close(_raw_stdin)
    _close(_raw_stdout)
    _close(_raw_stderr)

    # _all_processes._unlock()
    # _all_python_processes._unlock()

    if len(_all_python_processes) <= 1:
        # free our shared memory if we're the last python process remaining in the hierarchy:
        _all_processes.free()
        _all_python_processes.free()


_CurrentProcess = Process()  # per-process
print('current process state:', MultiMeta.get_info(_CurrentProcess, 'state'))
# noinspection PyProtectedMember
for th in _CurrentProcess._get_threads():
    _current_proc_threads.append(th)

