from multitools_2 import _const
import sys
from types import TracebackType
import pickle


try:
    raise TypeError("error")
except:

    """ei = sys.exc_info()
    tb: TracebackType = ei[2]
    print(str(tb))"""

    info = eval(_const.ASK_LAST_ERR)
    print(info)
    exc_info = info[0], eval(info[1]), None
    print(exc_info)
    # exc_info = info[0], eval(info[1]), eval(info[2])
    # print(exc_info)


