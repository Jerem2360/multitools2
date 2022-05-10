import os

from .._const import *
from .._meta import MultiMeta


if MS_WINDOWS:
    from . import _win_processes as _imp
else:
    from . import _posix_processes as _imp


_blocking_processes = []


class Process(metaclass=MultiMeta):
    def __new__(cls, *args, pid=0, **kwargs):
        self = super().__new__(cls)
        self._pid = pid
        daemon = kwargs.get('daemon', False)
        self._distant = kwargs.get('distant', False)
        if not daemon:
            _blocking_processes.append(self)
        self._set_info('daemon', daemon)
        return self

    def __init__(self, target=NO_OP_PROCESS_MAIN, daemon=False, **kwargs):
        self._target = target

    @classmethod
    def open(cls, pid, daemon=True):
        distant = True
        if pid == os.getpid():
            distant = False
        return cls.__new__(cls, pid=pid, daemon=daemon, distant=distant)

    def _set_info(self, name, value):
        setattr(self, f"#{name}", value)

    def _get_info(self, name):
        return getattr(self, f'#{name}')

