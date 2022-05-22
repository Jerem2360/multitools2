import _winapi
import io
import pickle
import types

from .._const import *
from .._meta import MultiMeta
from .._builtindefs import *
from .._typing import *
from .._errors import *
from .._helpers import *


if MS_WINDOWS:
    from . import _win_processes as _imp
else:
    from . import _posix_processes as _imp


_blocking_processes = []


def _all_attrs(obj):
    all_attrs = {}
    for attr_name in dir(obj):
        if attr_name not in ('__builtins__', '__dict__'):
            all_attrs[attr_name] = getattr(obj, attr_name)
    return all_attrs

def _get_modnames():
    res = []
    for modname in sys.modules.keys():
        res.append(modname)
    return tuple(res)


def _get_file_string_run_function(child_pipe, proc_obj, call_args, call_kwargs):
    try:
        p_args = pickle.dumps(call_args)
    except pickle.PickleError:
        raise ValueError("Arguments must pickleable.") from None

    try:
        p_kwargs = pickle.dumps(call_kwargs)
    except pickle.PickleError:
        raise ValueError("Arguments must be pickleable.") from None

    print('local:', repr(proc_obj))

    return f"""
import pickle, os, sys, time, _thread
try:
    import _winapi
except ModuleNotFoundError or ImportError:
    pass 
p2c, c2p, err = {repr(child_pipe)}
sys.stderr.write(str(p2c))
time.sleep(0.1)
proc_obj = pickle.loads({repr(proc_obj)})

setattr(proc_obj, '#pid', os.getpid())
setattr(proc_obj, '_pstate_expected', {STATE_RUNNING})
setattr(proc_obj, '#all_threads', (_thread.get_ident(),))

args = pickle.loads({repr(p_args)})
kwargs = pickle.loads({repr(p_kwargs)})
target_function = getattr(proc_obj, '#target')

sys.stderr.write(repr(target_function))
exit_code = target_function(proc_obj, *args, **kwargs)
if (exit_code is None) or not isinstance(exit_code, int):
    exit_code = 0
raise SystemExit(exit_code) from None
"""

def _copy_function(func: types.FunctionType, new_module, new_name):
    code_copy = types.CodeType(
        func.__code__.co_argcount,
        func.__code__.co_posonlyargcount,
        func.__code__.co_kwonlyargcount,
        func.__code__.co_nlocals,
        func.__code__.co_stacksize,
        func.__code__.co_flags,
        func.__code__.co_code,
        func.__code__.co_consts,
        func.__code__.co_names,
        func.__code__.co_varnames,
        func.__code__.co_filename,
        new_name,
        func.__code__.co_firstlineno,
        func.__code__.co_lnotab,
        func.__code__.co_freevars,
        func.__code__.co_cellvars,
    )

    func_copy = types.FunctionType(code_copy, func.__globals__,
                                   name=new_name, argdefs=func.__defaults__, closure=func.__closure__)
    func_copy.__module__ = new_module
    return func_copy


# noinspection PyDefaultArgument
class Process(metaclass=MultiMeta):
    """
    Class representing a process.

    When instantiated, this class produces a process model.
    This is a Process object that stores what the process will do when executed.

    Process models can store 2 different types of future activity:
    either a function representing the process' activity, or a command
    that will be executed to start the process.

    To start a process, simply call the appropriate process model, providing if
    necessary the parameters to pass to an eventual activity function. This will
    return a Process object storing an active process and information about it,
    called a process activity.

    Once terminated, a process activity is in an unusable state, and any attempt
    to obtain information about it will raise ProcessStateError, except for the exit
    status.
    """
    def __new__(cls, *args, **kwargs):
        """
        Create and return a new Process object.
        """
        pid = kwargs.get('pid', 0)
        distant = kwargs.get('distant', False)
        daemon = kwargs.get('daemon', False)
        pstate = kwargs.get('pstate', STATE_INITIALIZED)
        pipe_read = kwargs.get('pipe_read', 0)
        pipe_write = kwargs.get('pipe_write', 0)
        pipe_err = kwargs.get('pipe_err', 0)
        can_init = kwargs.get('_can_init', True)
        type_check((pid, distant, daemon, pstate, pipe_read, pipe_write, pipe_err, can_init), int, bool, bool, int, int, int, int, bool)

        # pickled_target = NO_OP_PROCESS_TARGET_PICKLED if target == NO_OP_PROCESS_TARGET else pickle.dumps(target)

        # target_copy = _copy_function(target, MODNAME_PROCESS, f"#{target.__name__}")
        # setattr(sys.modules[MODNAME_PROCESS], f"#{target.__name__}", target_copy)

        self = super().__new__(cls)
        self._owner = _imp.get_current_process()

        if (len(args) == 0) or isinstance(args[0], Function):
            target = args[0] if len(args) > 0 else kwargs.get('target', NO_OP_PROCESS_TARGET)
            type_check((target,), Function)
            if target == NO_OP_PROCESS_TARGET:
                target.__module__ = 'multitools_2._const'
            if pid != 0:
                self = MultiMeta.set_info(self, 'pid', pid)
            self = MultiMeta.set_info(self, 'target', target)
            # self = MultiMeta.set_info(self, 'pickled_target', pickled_target)
            if not can_init:
                self = MultiMeta.set_info(self, 'all_threads', ())  # list of owned thread ids

            self._command = None
            self._can_init = can_init
            self._distant = distant
            self._daemon = daemon
            self._pstate_expected = pstate
            self._pipes = (pipe_read, pipe_write, pipe_err)
            self._is_being_called = False
            self._stdin, self._stdout = 0, 0

            self.__name__ = target.__name__
            self.__qualname__ = target.__qualname__
            self.__defaults__ = target.__defaults__
            self.__kwdefaults__ = target.__kwdefaults__
            self.__annotations__ = target.__annotations__
            self.__builtins__ = target.__builtins__
            self.__closure__ = target.__closure__
            self.__code__ = target.__code__
            self.__globals__ = target.__globals__
            self.__module__ = target.__module__

        elif isinstance(args[0], str):
            target = kwargs.get('target', NO_OP_PROCESS_TARGET)
            type_check((target,), Function)
            self = MultiMeta.set_info(self, 'target', target)

            self._command = args[0]
            self._distant = False
            self._daemon = daemon
            self._pstate_expected = STATE_INITIALIZED
            self._pipes = (pipe_read, pipe_write, pipe_err)
            self._is_being_called = False
            self._stdin, self._stdout = 0, 0
            self._can_init = can_init

            self = MultiMeta.set_info(self, 'pid', 0)
            self = MultiMeta.set_info(self, 'all_threads', ())

            self.__name__ = self._command.split(' ')[0]
            self.__qualname__ = f"{MODNAME_PROCESS}.{self._command.split(' ')[0]}"
            self.__defaults__ = ()
            self.__kwdefaults__ = {}
            self.__annotations__ = {}
            self.__closure__ = None
            # noinspection PyTypeChecker
            self.__code__ = None
            self.__globals__ = globals()
            self.__module__ = MODNAME_PROCESS

        else:
            raise TypeError(TYPE_ERR_STR.format('function | str', type(args[0]).__name__)) from None

        return self


    def __init__(self, *args, **kwargs):
        """
        Initialize a new process.
        """
        flags = kwargs.get('flags', 0)
        environ = kwargs.get('environ', {})
        curdir = kwargs.get('curdir', "")
        type_check((flags, environ, curdir), int, dict, str)

        if (not self._can_init) or self._get_pstate() != STATE_INITIALIZED:  # target must already have been initialized
            return
        self._can_init = False

        MultiMeta.set_info(self, 'all_threads', ())
        self._options = _imp.ProcessStartOptions()
        self._options.flags = flags
        self._options.curdir = curdir
        self._options.environ = environ
        self._options.closefds = True

        if (len(args) == 0) or isinstance(args[0], Function):

            if MS_WINDOWS:
                self._options.startupinfo = _imp.ProcessStartupInfo()
                show_window = kwargs.get('show_window', False)
                self._options.create_console = kwargs.get('create_console')
                type_check((show_window,), bool)
                self._options.startupinfo.wShowWindow = _winapi.SW_HIDE if not show_window else _imp.SW_SHOW

        elif isinstance(args[0], str):
            if MS_WINDOWS:
                self._options.create_console = False
            else:
                target = kwargs.get('target', NO_OP_PROCESS_TARGET)
                type_check((target,), Function)
                self._options.preexec = target

        else:
            raise TypeError(TYPE_ERR_STR.format('function | str', type(args[0]).__name__)) from None

    def __call__(self, *args, **kwargs):
        """
        Call the actual process and return activity, given args and kwargs.

        Warning: Any argument passed in here must be pickleable. See the
        pickle module for more info.
        """
        if self._get_pstate() != STATE_INITIALIZED:
            raise ProcessStateError("Only process models can be called.") from None

        while self._is_being_called:
            pass  # make sure two different threads don't call simultaneously the same process object.
        self._is_being_called = True

        res = MultiMeta.copy(self)

        if self._command is None:
            p2c, c2p, err = _imp.create_new_pipe(), _imp.create_new_pipe(), _imp.create_new_pipe()
            res._options.p2c = p2c
            res._options.c2p = c2p
            res._options.err = err
            # print(p2c[0])

            _target = MultiMeta.get_info(self, 'target')
            _target_mod = sys.modules[_target.__module__]
            _orig_target = getattr(_target_mod, _target.__name__)

            # print(_target.__code__.co_names)
            # _target_copy = _copy_function(_target, MODNAME_PROCESS, f"#{_target.__name__}")
            # setattr(sys.modules[MODNAME_PROCESS], f"#{_target.__name__}", _target)

            process_code = _get_file_string_run_function((p2c[0], c2p[1], err[1]), pickle.dumps(res), args, kwargs)  # .removeprefix('\n').removesuffix('\n').replace("\n", ";").replace(":;", ":")
            print(f"<code>\n{process_code}\n</code>")
            command = f"\"{sys.executable}\" -c \"{process_code}\""
            proc_info, th_info, pipes = _imp.start_new_process(command, res._options)
            MultiMeta.set_info(res, 'pid', proc_info[0])

            res._stdin, res._stdout = proc_info[2]
            res._pipes = pipes

            res._pstate_expected = STATE_RUNNING
            if not res._daemon:
                _blocking_processes.append(res)
            old_threads = MultiMeta.get_info(res, 'all_threads')
            primary_thread = th_info[0]
            MultiMeta.set_info(res, 'all_threads', (*old_threads, primary_thread))

        else:
            shell = kwargs.get('shell', False)
            type_check((shell,), bool)
            if shell:
                proc_info, th_info, pipes = _imp.execute_command(res._command, res._options, curdir=res._options.curdir)
            else:
                proc_info, th_info, pipes = _imp.start_new_process(res._command, res._options)

            MultiMeta.set_info(res, 'pid', proc_info[0])
            res._stdin, res._stdout = proc_info[2]
            res._pipes = pipes
            res._pstate_expected = STATE_RUNNING
            _blocking_processes.append(res)
            old_threads = MultiMeta.get_info(res, 'all_threads')
            primary_thread = th_info[0]
            MultiMeta.set_info(res, 'all_threads', (*old_threads, primary_thread))

        res._is_being_called = False
        self._is_being_called = False

        for i in range(1000):
            print(str(_winapi.ReadFile(pipes[2], 100)[0], encoding=DEFAULT_ENCODING).replace('\n', ''),
                  file=sys.stderr)

        return res

    def __getstate__(self):
        """
        Helper so that pickle handles correctly the target function, without
        searching for its module.
        Instead, it will pickle the function's attributes one by one in a dictionary.
        This allows to pickle non-statically defined functions.
        """
        target = MultiMeta.get_info(self, 'target')

        return {
            'pid': MultiMeta.get_info(self, 'pid', default=0),
            'all_threads': MultiMeta.get_info(self, 'all_threads', default=()),
            'daemon': self._daemon,
            'can_init': self._can_init,
            'owner': self._owner if '_owner' in dir(self) else None,
            'pstate': self._pstate_expected,
            'pipes': self._pipes,
            **pickle_function(target, 'target'),
        }

    def __setstate__(self, state):
        """
        Helper so that pickle handles correctly the target function, without
        searching for its module.
        Instead, it will pickle the function's attributes one by one in a dictionary.
        This allows to pickle non-statically defined functions.
        """
        target = unpickle_function(state, 'target')

        if state['pid'] != 0:
            MultiMeta.set_info(self, 'pid', state['pid'])
        MultiMeta.set_info(self, 'target', target)
        MultiMeta.set_info(self, 'all_threads', state['all_threads'])
        self._can_init = state['can_init']

        if state['owner'] is None:
            self._daemon = self._distant = True
        elif state['pid'] == 0:
            self._distant = (_imp.get_current_process() != state['owner'])
            self._daemon = True if self._distant else state['daemon']
        else:
            self._distant = (_imp.get_current_process() != state['pid'])
            self._daemon = True if self._distant else state['daemon']

        self._pstate_expected = state['pstate']
        self._pipes = state['pipes']

        self.__name__ = target.__name__
        self.__qualname__ = target.__qualname__
        self.__defaults__ = target.__defaults__
        self.__kwdefaults__ = target.__kwdefaults__
        self.__annotations__ = target.__annotations__
        self.__closure__ = target.__closure__
        self.__code__ = target.__code__
        self.__globals__ = target.__globals__
        self.__module__ = target.__module__

    def __repr__(self):
        if self._pstate_expected == STATE_INITIALIZED:
            return f"<process model '{self.__name__}'>"
        return f"<process at {hex(id(self))}, pid={MultiMeta.get_info(self, 'pid')}>"

    @staticmethod
    def main_process():
        """
        Return the main process' activity.
        """
        return _MainProc

    def terminate(self, force=False):
        """
        Terminate a process. Return whether this function succeeded.
        """
        if not force:
            state = self._get_pstate()
            if state == STATE_INITIALIZED:
                raise ProcessStateError("Process models cannot be terminated.") from None
            if state == STATE_FINALIZED:
                return True
        return _imp.terminate_process(MultiMeta.get_info(self, 'pid'))

    def kill(self):
        """
        Kill a process. Return whether this function succeeded.
        """
        state = self._get_pstate()
        if state == STATE_INITIALIZED:
            raise ProcessStateError("Process models cannot be killed.") from None
        if state == STATE_FINALIZED:
            return True
        return _imp.kill_process(MultiMeta.get_info(self, 'pid'))

    @classmethod
    def current_process(cls):
        """
        Get the current process' activity.
        """
        return cls.__open__(_imp.get_current_process())

    @classmethod
    def __open__(cls, pid):
        """
        Open and return an already running process' activity, given its pid.
        """
        type_check((pid,), int)
        if pid in (0, 4):
            raise PermissionError("Access denied.")
        _distant = _daemon = (pid != _imp.get_current_process())
        return Process.__new__(cls, pid=pid, distant=_distant, daemon=_daemon, tstate=STATE_RUNNING, _can_init=False)

    def _exit_status(self):
        try:
            return _imp.get_process_exit_code(MultiMeta.get_info(self, 'pid'))
        except ProcessLookupError:
            return 0

    def _get_pstate(self):
        if self._pstate_expected == STATE_INITIALIZED:
            return STATE_INITIALIZED
        if self._exit_status() == _imp.STILL_ACTIVE:
            return STATE_RUNNING
        return STATE_FINALIZED

    def _read_data_from_child(self):
        stdin = io.open(self._pipes[0], closefd=False, mode='br')
        head_b = stdin.read(4)
        head = int.from_bytes(head_b, "big")
        data = stdin.read(head)
        stdin.close()
        return data

    def _write_data_to_child(self, data):
        head = len(data)
        head_b = int.to_bytes(head, 4, "big")
        print(f"head: {repr(head_b)}, {head}, {int.from_bytes(head_b, 'big')}")
        data_b = bytes(data, encoding=DEFAULT_ENCODING) if not isinstance(data, bytes) else data
        print(f"data: {repr(data_b)}")
        _imp.write_descr(self._pipes[1], head_b)
        _imp.write_descr(self._pipes[1], data_b)
        return head

    def _open_child_thread(self, tid):
        pass

    pid = property(lambda self: MultiMeta.get_info(self, 'pid', 0))
    state = property(lambda self: self._get_pstate())

_MainProc = Process.__open__(MAIN_PROCESS_ID)


def __finalize__():
    for proc in _blocking_processes:
        proc.terminate(force=True)

