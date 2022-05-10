from ._threads import Thread
from . import _threads


def __finalize__(*exc_info):
    _threads.__finalize__()

