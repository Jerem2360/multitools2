from types import TracebackType
import sys
from ._meta import MultiMeta


__all__ = [
    "SUCCESS",
    "FAILURE",
]


class Result(metaclass=MultiMeta):
    def __init__(self, boolvalue: bool, numvalue: int, exc_info: tuple[TracebackType | None, type[Exception] | None, Exception | None], retval=None):
        self._bool = boolvalue
        self._num = numvalue
        self._exc_info = exc_info
        self._result = retval

    @property
    def traceback(self) -> TracebackType:
        return self._exc_info[0]

    @property
    def exc_type(self) -> type[Exception]:
        return self._exc_info[1]

    @property
    def exc_value(self) -> Exception:
        return self._exc_info[2]

    @property
    def result(self):
        return self._result

    def __bool__(self) -> bool:
        return self._bool

    def __int__(self) -> int:
        return int(self._num)

    def __float__(self) -> float:
        return float(self._num)


def SUCCESS(result=None):
    return Result(True, 0, (None, None, None), retval=result)


def FAILURE():
    return Result(False, -1, *sys.exc_info())

