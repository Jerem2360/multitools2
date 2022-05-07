import _winapi
import os

from . import _thread
from .._meta import MultiMeta
from .._const import *


def _list_to_command(seq):
    """
    Borrowed from subprocess.list2cmdline()
    """
    result = []
    needquote = False
    for arg in map(os.fsdecode, seq):
        bs_buf = []

        # Add a space to separate this argument from the others
        if result:
            result.append(' ')

        needquote = (" " in arg) or ("\t" in arg) or not arg
        if needquote:
            result.append('"')

        for c in arg:
            if c == '\\':
                # Don't know if we need to double yet.
                bs_buf.append(c)
            elif c == '"':
                # Double backslashes.
                result.append('\\' * len(bs_buf) * 2)
                bs_buf = []
                result.append('\\"')
            else:
                # Normal char
                if bs_buf:
                    result.extend(bs_buf)
                    bs_buf = []
                result.append(c)

        # Add remaining backslashes, if any.
        if bs_buf:
            result.extend(bs_buf)

        if needquote:
            result.extend(bs_buf)
            result.append('"')

    return ''.join(result)


class _ProcessStartupInfo:
    def __init__(self, dwFlags=0, hStdInput=None, hStdOutput=None,
                 hStdError=None, wShowWindow=0, lpAttributeList=None):
        self.dwFlags = dwFlags
        self.hStdInput = hStdInput
        self.hStdOutput = hStdOutput
        self.hStdError = hStdError
        self.wShowWindow = wShowWindow
        self.lpAttributeList = lpAttributeList or {"handle_list": []}

    def copy(self):
        attr_list = self.lpAttributeList.copy()
        if 'handle_list' in attr_list:
            attr_list['handle_list'] = list(attr_list['handle_list'])

        return _ProcessStartupInfo(
            dwFlags=self.dwFlags,
            hStdInput=self.hStdInput,
            hStdOutput=self.hStdOutput,
            hStdError=self.hStdError,
            wShowWindow=self.wShowWindow,
            lpAttributeList=attr_list
        )


class Process(metaclass=MultiMeta):

    def __init__(self, program, args, startupinfo, env_vars=None, curdir=None, inherit=False, use_threading=False):
        # startupinfo = _ProcessStartupInfo()

        if curdir is not None:
            curdir = os.fsdecode(curdir)

        p_in, p_out = os.pipe()

        init_subprocess = f"""
        import os;
        p_in, p_out = {p_in}, {p_out};
        os.write(p_out, "")
        """

        p_handle, t_handle, p_id, t_id = _winapi.CreateProcess(
            program,  # app_name
            f"\"{program}\" {args}",  # command
            None,  # proc_attrs
            None,  # thread_attrs
            inherit,  # inherit_handles
            0,  # creation_flags
            env_vars,  # env_mapping  (env vars)
            curdir,  # current_directory
            startupinfo.copy(),  # startupinfo
        )

        self.__threads__ = [_thread.Thread.__from_attrs__(
            tstate=TSTATE_RUNNING,
            lock=None,
        )]
        self.__id__ = p_id
        self.__handle__ = p_handle

    @property
    def active_threads(self):
        if self.__threads__ is None:  # this happens for the main process
            return (th for th in _thread.__all_threads)
        return (th for th in self.__threads__.values())

    @staticmethod
    def get_main():
        return _MainProcess


_MainProcess = Process.__new__(Process)
_MainProcess.__threads__ = None

