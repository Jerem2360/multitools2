from .._meta import *
from .._const import *
from .._builtindefs import *
from .. import _win32
from ._database import _all_processes, _all_python_processes, _current_proc_threads, \
    DataBaseElement, NUL_HVal


"""

"""


TH_OPEN = 0
TH_CREATE = 1


class Thread(metaclass=MultiMeta):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        return self

    def __init__(self, arg1, **kwargs):
        """
        Thread(tid) -> Thread  {TH_OPEN}
        Thread(activity, daemon=False) -> Thread {TH_CREATE}
        """
        if isinstance(arg1, int):  # user wants to open a thread
            MultiMeta.set_info(self, 'state', STATE_RUNNING)
            MultiMeta.set_info(self, 'id', arg1)
            if MS_WINDOWS:
                MultiMeta.set_info(self, 'handle', _win32.open_thread(arg1))

        elif isinstance(arg1, (Function, Method)):
            MultiMeta.set_info(self, 'state', STATE_INITIALIZED)

    def __repr__(self):
        # temporary
        return f"<thread {self.tid}>"

    @classmethod
    def __open__(cls, tid):
        return cls(tid)

    tid = property(lambda self: MultiMeta.get_info(self, 'id'))

