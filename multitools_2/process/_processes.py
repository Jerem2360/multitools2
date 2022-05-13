import os
import sys

from .._const import *
from .._meta import MultiMeta
from .._local import *


if MS_WINDOWS:
    from . import _win_processes as _imp
else:
    from . import _posix_processes as _imp


_blocking_processes = []
_win32 = defined('_imp.ProcessStartupInfo')


code_format = """

"""


# noinspection PyDefaultArgument
class Process(metaclass=MultiMeta):
    def __new__(cls, *args, pid=0, **kwargs):
        self = super().__new__(cls)
        self._pid = pid
        self._daemon = kwargs.get('daemon', False)
        self._distant = kwargs.get('distant', False)
        if not self._daemon:
            _blocking_processes.append(self)
        self._set_info('daemon', daemon)
        if 'target' in kwargs:
            target = kwargs.get('target')
            self._target = target
        return self

    def __init__(self, target=NO_OP_PROCESS_MAIN, env={}, close_fds=False, curdir='', flags=0, target=NO_OP_PROCESS_MAIN, daemon=False, **kwargs):
        if '_target' not in dir(self):
            self._target = target

        if self._pid == 0:
            options = _imp.ProcessStartOptions()
            options.close_fds = close_fds
            options.curdir = curdir
            options.environ = env
            if MS_WINDOWS:
                options.startupinfo = _imp.ProcessStartupInfo(dwFlags=flags)

            p_info, tid, pipes = _imp.start_new_process(f"{sys.executable} -c {}", options)

    @classmethod
    def open(cls, pid, daemon=True):
        distant = True
        if pid == os.getpid():  # current process
            distant = False
        return cls.__new__(cls, pid=pid, daemon=daemon, distant=distant)

    def _set_info(self, name, value):
        setattr(self, f"#{name}", value)

    def _get_info(self, name):
        return getattr(self, f'#{name}')

