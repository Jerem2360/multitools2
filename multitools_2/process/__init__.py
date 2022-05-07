from ._thread import Thread
from ._process import Process
from . import _thread


def __finalize__(*exc_info):
    _thread.__finalize__()

