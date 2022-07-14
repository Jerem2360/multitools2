import _io
from typing import overload, Any, Callable, NoReturn
from types import FunctionType as _Ft, FrameType
from types import TracebackType as _Tbt
from ..io import Stream as _Stream

_ProcActivity = Callable[[Process, ...], int]
_ThActivity = Callable[[Thread, ...], Any]
_TraceFunc = Callable[[FrameType, str, tuple], None]

import sys


class Process:
    """
    Class representing processes.
    """
    def __new__(cls, *args, **kwargs) -> Process: ...
    if sys.platform == 'win32':
        @overload
        def __init__(self, activity: _ProcActivity, flags: int = ..., environ: dict[str, Any] = ..., curdir: str = ...,
                     show_window: bool = ..., create_console: bool = ...) -> None: ...
        @overload
        def __init__(self, command: str, flags: int = ..., environ: dict[str, Any] = ..., curdir: str = ...) -> None: ...
    else:
        @overload
        def __init__(self, activity: _ProcActivity, flags: int = ..., environ: dict[str, Any] = ..., curdir: str = ...) -> None: ...
        @overload
        def __init__(self, command: str, flags: int = ..., environ: dict[str, Any] = ..., curdir: str = ...,
                     target: _Ft = ...) -> None: ...
    def __dir__(self) -> list[str]: ...
    def __getstate__(self) -> dict[str, Any]: ...
    def __setstate__(self, state: dict[str, Any]) -> None: ...
    def __mul__(self, other: int) -> int | Process: ...
    def __call__(self, *args, **kwargs) -> Process | None: ...
    def __repr__(self) -> str: ...
    @classmethod
    def __open__(cls, pid: int) -> Process: ...
    def terminate(self) -> bool | NoReturn: ...
    def kill(self) -> bool | NoReturn: ...
    def exc_info(self) -> tuple[type[Exception], Exception, _Tbt] | tuple[None, None, None] | None: ...
    def get_thread(self, tid: int) -> Thread: ...
    @classmethod
    def get_current_process(cls) -> Process: ...
    exit_status: int | None = ...
    state: int = ...
    pid: int = ...
    known_threads: tuple[Thread, ...] = ...
    stdin: _Stream = ...
    stdout: _Stream = ...
    stderr: _Stream = ...


class Thread:
    def __new__(cls, *args, **kwargs) -> Thread: ...
    @overload
    def __init__(self, daemon: bool = ...) -> None: ...
    @overload
    def __init__(self, activity: _ThActivity, daemon: bool = ...) -> None: ...
    def __mul__(self, other: int) -> int | Thread: ...
    def __call__(self, *args, **kwargs) -> Thread | None: ...
    def __repr__(self) -> str: ...
    def invoke(self, function: _Ft, *args, **kwargs) -> None: ...
    def exc_info(self) -> tuple[type[Exception], Exception, _Tbt] | tuple[None, None, None]: ...
    def settrace(self, function: _TraceFunc) -> None: ...
    def gettrace(self) -> _TraceFunc: ...
    def join(self) -> None: ...
    @staticmethod
    def sleep(ms: int) -> None: ...
    tid: int = ...
    daemon: bool = ...
    owner: Process = ...

