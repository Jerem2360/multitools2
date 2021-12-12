from ._stream import Stream as _StreamBase
import _io
from typing import overload


class TextIO(_StreamBase):
    """
    Basic text input/output stream.
    """
    @overload
    def __init__(self, fp):
        """
        Open for reading and writing to specified file.
        """

    @overload
    def __init__(self, s, is_file=False, file=None):
        """
        Read and write to the provided already open file stream.
        """

    def __init__(self, value, is_file=False, file=None):
        if not is_file:
            file = None
        if file is None:
            is_file = False

        if isinstance(value, str):
            self.__file = True
            self.__path = value
            super().__init__(open(self.__path), str)
        elif isinstance(value, _io.TextIOWrapper):
            self.__file = is_file
            self.__path = file
            self.__io = value
        else:
            raise TypeError(f"Expected type 'str' or '_io.TextIOWrapper', got '{type(value).__name__}' instead.")

    def __reset_handle(self, mode):
        """
        Internal method.
        """
        self.handle = open(self.__path, mode)

    def __read__(self, *args, **kwargs):
        """
        Implement self.read()
        """
        if self.__file:
            self.__reset_handle('r+')

            return super().__read__(*args, **kwargs)
        return super().__read__(*args, **kwargs)

    def __write__(self, data, flush=False, overwrite=True):
        """
        Implement self.write()
        """
        if self.__file:
            m = 'a+'
            if overwrite:
                m = 'w+'
            self.__reset_handle(m)

            return super().__write__(data, flush=flush)
        return super().__write__(data, flush=flush)

    def __readable__(self):
        """
        Implement property self.readable
        """
        if self.__file:
            return True
        return super().__readable__()

    def __writable__(self):
        """
        Implement property self.writable
        """
        if self.__file:
            return True
        return super().__writable__()
