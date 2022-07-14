from ._stream import Stream
from .._meta import MultiMeta as _Mt
from .._const import MS_WINDOWS as _MS_WINDOWS
if _MS_WINDOWS:
    from .._win32 import open as _open, pipe as _pipe
else:
    from os import open as _open, pipe as _pipe


class File(Stream, metaclass=_Mt):
    def __init__(self, descr, readable, writable):
        """
        Initialize a new File object.
        """
        super().__init__(descr, readable=readable, writable=writable)

    @classmethod
    def open(cls, filename, mode='r'):
        """
        Open a file for reading, writing, creating or appending from a given path.
        """
        readable = 'r' in mode
        writable = ('w' in mode) or ('a' in mode) or ('x' in mode)
        descr = _open(filename, mode=mode)
        return cls(descr, readable, writable)


class Pipe(Stream, metaclass=_Mt):
    def __new__(cls, *args, **kwargs):
        """
        Create a new pipe and return a tuple of the two pipe ends.
        """
        descr1, descr2 = _pipe()
        stream1 = super().__new__(cls)
        stream2 = super().__new__(cls)
        stream1._initialized = False
        stream2._initialized = False
        stream1.__init__(descr1, readable=True, writable=False)
        stream2.__init__(descr2, readable=False, writable=True)
        return stream1, stream2

    def __init__(self, *args, **kwargs):
        """
        Initialize a new Pipe object.
        """
        if (len(args) != 1) and (len(kwargs) != 3):
            return
        # noinspection PyUnresolvedReferences
        if self._initialized:  # make sure we only get initialized once
            return
        self._initialized = True
        super().__init__(*args, **kwargs)

