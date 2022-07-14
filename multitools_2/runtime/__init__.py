from ._process2 import Process
from ._thread import Thread
from . import _process2, _thread


def __finalize__(*exc_info):
    _thread.__finalize__()
    _process2.__finalize__()

