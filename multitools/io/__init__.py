from ._stream import *
from ._buffer import *
import sys
import _io


__all__ = [
    "Stream",
    "OStream",
    "IStream",
    "TextOutput",
    "TextInput",
    "TextIO",
    "BytesOutput",
    "BytesInput",
    "BytesIO",
    "FileOutput",
    "FileInput",
    "FileIO",
    "Buffer",
    "BytesBuffer",
    "StrBuffer",
    "FileBuffer",
    "stdout",
    "stdin",
    "stderr",
    "py_stdout",
    "py_stdin",
    "py_stderr",
    "print",
    "printf",
    "input",
]


stdout: FileOutput[str] = FileOutput(FileBuffer(1))
stdin: FileInput[str] = FileInput(FileBuffer(0))
stderr: FileOutput[str] = FileOutput(FileBuffer(2))

# noinspection PyTypeChecker
py_stdout: _io.TextIOWrapper = sys.stdout
# noinspection PyTypeChecker
py_stdin: _io.TextIOWrapper = sys.stdin
# noinspection PyTypeChecker
py_stderr: _io.TextIOWrapper = sys.stderr


def print(data: str, *more_data: str, split: str = "", end: str = "\n", encoding: str = None) -> int:

    for dat in more_data:
        data += split
        data += dat
    data += end
    return stdout.write(data, encoding=encoding)


def printf(data: str, *_format: str, end: str = "\n", encoding: str = None) -> int:
    data += end
    return stdout.write(data.format(*_format), encoding=encoding)


def input() -> str:
    return stdin.readline()

