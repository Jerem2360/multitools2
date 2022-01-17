import ctypes
import sys


from ..results import *


def ask_for_admin():
    res = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    if res >= 32:
        return SUCCESS(res)
    return FAILURE()


def is_user_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return FAILURE()

