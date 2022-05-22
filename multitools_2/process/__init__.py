from ._threads import Thread
from . import _threads
from . import _threads2
from ._processes import Process


def _curproc(): return Process.current_process()


_threads2._get_current_process = _curproc


def _exit(code: int):
    raise SystemExit(code) from None


def __finalize__(*exc_info):
    _threads.__finalize__()
    _processes.__finalize__()

