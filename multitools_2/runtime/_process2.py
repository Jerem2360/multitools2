import os

from .._meta import MultiMeta
from .._errors import *
from .._typing import *
from .._builtindefs import *
from ._shared_memory import SharedDict
from .._const import *
from .._helpers import *
if MS_WINDOWS:
    from .._win32 import pipe as _pipe, getpid as _getpid, close as _close
    from .. import _win32
else:
    from os import pipe as _pipe, getpid as _getpid, close as _close


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

__blocking_processes = {}


# if we are the main process, create the shared memory, otherwise just open it.
if _getpid() == MAIN_PROCESS_ID:
    _all_processes = SharedDict.from_dict({'counter': 0})
    _all_python_processes = SharedDict(create=True)

else:
    _all_procs_name = os.environ.get(ENV_PROCS, '<unknown>')
    _all_py_procs_name = os.environ.get(ENV_PY_PROCS, '<unknown>')
    if '<unknown>' in (_all_procs_name, _all_py_procs_name):
        raise SystemError(f"One or more environment variables were missing.\nEnvironment variables were:\n{os.environ}")
    _all_processes = SharedDict(name=_all_procs_name, create=False)
    _all_python_processes = SharedDict(name=_all_py_procs_name, create=False)

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
        self = MultiMeta.set_info(self, 'lid', None)

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
                elif isinstance(args[0], Function):
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
            local_id = self._find_lid_in_processes(pid)
            if local_id is None:
                local_id = self._add_to_processes({}, False)

            if ('id' not in self._get_process_state(local_id)) or (self._get_process_state(local_id)['id'] != pid):
                self._update_process_state(local_id, 'id', pid)

            if ('tp' not in self._get_process_state(local_id)) or (self._get_process_state(local_id)['tp'] != tp):
                self._update_process_state(local_id, 'tp', tp if tp != PROC_CURRENT else PROC_OPENED)

            if ('state' not in self._get_process_state(local_id)) or (self._get_process_state(local_id)['state'] != tp):
                self._update_process_state(local_id, 'state', state)

            if 'run' not in self._get_process_state(local_id):
                self._update_process_state(local_id, 'run', run if tp != PROC_CURRENT else None)

            if MS_WINDOWS:
                MultiMeta.set_info(self, 'handle', handle)
            MultiMeta.set_info(self, 'lid', local_id)

        else:  # user wants to create a process model
            MultiMeta.set_info(self, 'state', state)
            if tp == PROC_CREATED_FUNCTION:
                MultiMeta.set_info(self, 'target', run)
            else:
                MultiMeta.set_info(self, 'command', run)
            MultiMeta.set_info(self, 'options', ProcessOptions(**kwargs))

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
            'lid': MultiMeta.get_info(self, 'lid') if MultiMeta.has_info(self, 'lid') else None,
            'tp': tp,
            'run': run if tp != PROC_CREATED_COMMAND else pickle_function2(run),
            'state': self._get_state(),
            'options': MultiMeta.get_info(self, 'options') if MultiMeta.has_info(self, 'options') else None
        }

    def __setstate__(self, state):
        local_id = state['lid']
        if local_id in _all_processes:  # excludes the case where local_id is None so the case of process models
            MultiMeta.set_info(self, 'lid', local_id)
            MultiMeta.set_info(self, 'state', STATE_RUNNING)

            tp = state['tp']
            if self.pid == _getpid():
                tp = PROC_CURRENT

            if MS_WINDOWS:
                MultiMeta.set_info(self, 'handle', _win32.open_process(self.pid))
            MultiMeta.set_info(self, 'tp', tp)



    def __call__(self, *args, **kwargs):

        proc = MultiMeta.copy(self)


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

    @staticmethod
    def _get_process_state(lid):
        return _all_processes[lid]

    @staticmethod
    def _update_process_state(lid, key, value):
        state = _all_processes[lid]
        state[key] = value
        _all_processes[lid] = state

    @staticmethod
    def _find_lid_in_processes(pid):
        for key, value in _all_processes.items():
            if (key == 'counter') or ('id' not in value):
                continue
            if (value['id'] == pid) and (value['state'] == STATE_RUNNING):
                return key
        return None

    @staticmethod
    def _add_to_processes(state, python):
        counter = _all_processes['counter']
        _all_processes['counter'] += 1
        _all_processes[counter] = state
        if python:
            _all_python_processes[counter] = None
        return counter

    def _get_state(self):
        if not MultiMeta.has_info(self, 'state'):
            return self._get_process_state(MultiMeta.get_info(self, 'lid'))['state']
        simple_state = MultiMeta.get_info(self, 'state')
        if simple_state == STATE_INITIALIZED:
            return simple_state
        return self._get_process_state(MultiMeta.get_info(self, 'lid'))['state']

    def _get_type(self):
        if self.pid == _getpid():
            return PROC_CURRENT
        return self._get_process_state(MultiMeta.get_info(self, 'lid'))['tp']

    def _build_code(self, pipes, call_args, call_kwargs):
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

        return f"""
import sys, time, io, pickle, os
os.environ['{MAIN_PROC_ENV_NAME}'] = '{MAIN_PROCESS_ID}'
os.environ['{ENV_PROCS}'] = '{_all_processes.name}'
os.environ['{ENV_PY_PROCS}'] = '{_all_python_processes.name}'

_MS_WINDOWS = sys.platform == 'win32'
if _MS_WINDOWS:
    import _winapi

in, out, err, e_info = ({int(pipes[0])}, {int(pipes[1])}, {int(pipes[2])}, {int(pipes[3])})
time.sleep(0.1)

proc_b = {proc_code_snip}
f = io.BytesIO(proc_b)
proc = pickle.Unpickler(f).load()

args_b = {args_code_snip}
args = pickle.loads(args_b)

kwargs_b = {kwargs_code_snip}
kwargs = pickle.loads(kwargs_b)

func = getattr(proc, '#target')
try:
    exit_code = func(proc, *args, **kwargs)
except SystemExit as e:
    exit_code = e.code
except KeyboardInterrupt:
    exit_code = -1
except:
    sys.excepthook(*sys.exc_info())
    raise SystemExit(1) from None

if not isinstance(exit_code, int):
    exit_code = 0
    if hasattr(exit_code, __bool__):
        exit_code = bool(exit_code)
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

    @property
    def pid(self):
        if self._get_state() == STATE_INITIALIZED:
            return 0
        # print(_all_processes)
        return self._get_process_state(MultiMeta.get_info(self, 'lid'))['id']


def __finalize__():
    for pid, proc in __blocking_processes:
        try:
            proc.join()
        except ProcessError:
            pass

    if len(_all_python_processes) <= 1:
        # free our shared memory if we're the last python process remaining in the hierarchy:
        _all_processes.free()
        _all_python_processes.free()


_CurrentProcess = Process()

