from typing import Generic, TypeVar
from ..errors import *


_DT = TypeVar("_DT")


class Stream(Generic[_DT]):
    def __init__(self, handle, io_type, read='read', write='write'):
        """
        A basic stream type based on a handle, the type of data
        the handle accepts and eventually the handle's reading and
        writing methods' names.
        """
        self.__h = handle
        self.__io_tp = io_type
        self.__read = read
        self.__write = write

    def __read__(self, *args, **kwargs):
        """
        Reader base that can be overridden to customize.
        When overriding, make sure to call super().__read__()
        at some point.
        """
        read = getattr(self.handle, self.__read)
        return read(*args, **kwargs)

    def __write__(self, data: _DT, flush=False, **kwargs):
        """
        Writer base that can be overridden to customize.
        When overriding, make sure to call super().__write__()
        at some point.
        """
        write = getattr(self.handle, self.__write)
        res = write(data, **kwargs)
        if flush:
            self.handle.flush()
        return res

    def read(self, *args, **kwargs):
        """
        Read data from the handle.
        """
        if self.readable:
            return self.__read__(*args, **kwargs)
        raise PermissionError("Not readable!")

    def write(self, data: _DT, *extra, sep="", end="\n", flush=False, **kwargs):
        if isinstance(data, self.__io_tp):
            for extra_data in extra:
                if isinstance(sep, self.__io_tp):
                    data += sep
                if isinstance(extra_data, self.__io_tp):
                    data += extra_data

            if isinstance(end, self.__io_tp):
                data += end

            if self.writable:
                return self.__write__(data, flush=flush, **kwargs)
            raise PermissionError("Not writable!")
        raise SimpleTypeError(type(data), self.__io_tp, source='data')

    def __readable__(self):
        """
        Override to customize property self.readable
        When overriding, make sure to call super().__readable__()
        at some point.
        """
        if hasattr(self.__h, 'readable'):
            return self.__h.readable

    def __writable__(self):
        """
        Override to customize property self.writable
        When overriding, make sure to call super().__writable__()
        at some point.
        """
        if hasattr(self.__h, 'writable'):
            return self.__h.writable

    @property
    def handle(self):
        return self.__h

    @handle.setter
    def handle(self, value):
        if isinstance(value, type(self.__h)):
            self.__h = value
            return
        raise SimpleTypeError(type(value), type(self.__h), source='handle')

    @property
    def readable(self):
        """
        Whether the stream can be read or not.
        """
        return self.__readable__()

    @property
    def writable(self):
        """
        Whether the stream can be written to or not.
        """
        return self.__writable__()

    @property
    def fileno(self):
        val = self.__h.fileno
        if isinstance(val, int):
            return val
        if hasattr(val, '__call__'):
            res = val()
            if isinstance(res, int):
                return res
        raise AttributeError("Data 'fileno' cannot be deduced from the handle.")
