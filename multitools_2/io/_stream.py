import _io
import locale

from .._meta import *
from .._typing import *
from .._const import *
from .._errors import *
if MS_WINDOWS:
    from .._win32 import open, close, read, write  # for supporting win32 handles.
else:
    from os import open, close, read, write


class Stream(metaclass=MultiMeta):
    def __init__(self, arg1, readable=True, writable=False, name=None, encoding=None):
        # noinspection PyUnresolvedReferences
        type_check((arg1, name), (_io._IOBase, int), (str, None))
        self._source = arg1
        self._closed = False
        self._readable = readable
        self._writable = writable

        if name is None:
            if isinstance(self._source, int):
                name = str(self._source)
            else:
                name = self._source.name if hasattr(self._source, 'name') else str(self._source.fileno())

        # noinspection PyUnresolvedReferences
        if isinstance(self._source, _io._TextIOBase):
            self._raw_datatype = str
        elif isinstance(self._source, (_io._IOBase, int)):
            self._raw_datatype = bytes
        else:
            self._raw_datatype = bytes

        if encoding is None:
            self._datatype = self._raw_datatype
        else:
            self._datatype = str

        if encoding in ('default', None):
            self._encoding = locale.getpreferredencoding(False)
        else:
            self._encoding = encoding

        self._name = name

    def _encode(self, text):
        if self._raw_datatype == self._datatype:
            return text
        if isinstance(text, self._raw_datatype):
            return text
        if isinstance(text, str):  # need to pass from str to bytes
            return text.encode(self._encoding)
        if isinstance(text, bytes):  # need to pass from bytes to str
            return text.decode(self._encoding)
        return text

    def _decode(self, text):
        if self._raw_datatype == self._datatype:
            return text
        if isinstance(text, self._datatype):
            return text
        if isinstance(text, bytes):  # need to pass from bytes to str
            return text.decode(self._encoding)
        if isinstance(text, str):  # need to pass from str to bytes
            return text.encode(self._encoding)
        return text

    def _check_closed(self):
        if self._closed:
            raise ValueError('I/O operation on closed file.')

    def _check_readable(self):
        if not self.readable():
            raise UnsupportedOperation('not readable.')

    def _check_writable(self):
        if not self.writable():
            raise UnsupportedOperation('not writable.')

    def _check_seekable(self):
        if not self.seekable():
            raise UnsupportedOperation('not seekable.')

    def __write__(self, data):
        """
        Callback that determines the writing functionality of the stream.
        Can be safely overridden.
        """
        type_check((data,), self._raw_datatype)
        if isinstance(self._source, int):
            return write(self._source, data)
        return self._source.write(data)

    def __read__(self, size):
        """
        Callback that determines the reading functionality of the stream.
        Can be safely overridden.
        """
        type_check((size,), int)
        # noinspection PyUnresolvedReferences
        if isinstance(self._source, int):
            return read(self._source, size)
        return self._source.read(size)

    def __close__(self):
        """
        Callback that determines the closing functionality of the stream.
        Can be safely overridden.
        """
        if isinstance(self._source, int):
            return close(self._source)
        self._source.close()

    def __fileno__(self):
        """
        Callback that determines the method of obtaining the underlying file descriptor of the
        stream when it was not directly passed in to the constructor.
        Can be safely overridden.
        """
        return self._source.fileno()

    def __flush__(self):
        """
        Callback that determines the flushing functionality of the stream when a file descriptor
        was not directly passed in to the constructor.
        Can be safely overridden.
        """
        self._source.flush()

    def __isatty__(self):
        """
        Callback that determines how to know if the stream is an interactive stream, when a file descriptor
        was not directly passed in to the constructor.
        Can be safely overridden.

        Advice: When this cannot be determined, return False.
        """
        return self._source.isatty()

    def read(self, size=-1):
        self._check_readable()
        self._check_closed()
        type_check((size,), int)
        if size >= 0:
            return self.__read__(size)

        data = self._datatype()
        while True:
            try:
                data += self.__read__(1)
            except EOFError or BrokenPipeError:
                break
            except:
                break
        return self._decode(data)

    def write(self, data):
        self._check_writable()
        self._check_closed()
        type_check((data,), self._datatype)
        return self.__write__(self._encode(data))

    def readline(self, **kwargs):
        self._check_readable()
        self._check_closed()
        data = self._datatype()
        while True:
            try:
                char = self.__read__(1)
            except EOFError or BrokenPipeError:
                break
            data += char
            if char in ('\n', b'\n'):
                break

        return self._decode(data[:-2])  # remove the newline character

    def readlines(self, hint=1):
        self._check_readable()
        self._check_closed()
        type_check((hint,), int)

        lines = []
        for i in range(hint):

            line = self._datatype()

            while True:
                try:
                    char = self.__read__(1)
                except EOFError or BrokenPipeError:
                    break
                line += char
                if char in ('\n', b'\n'):
                    break

            lines.append(self._decode(line))
        return lines

    def writelines(self, lines):
        self._check_writable()
        self._check_closed()
        for line in lines:
            type_check((line,), self._datatype)
            self.__write__(self._encode(line))

    def close(self):
        self.__close__()
        self._closed = True

    def fileno(self):
        self._check_closed()
        if isinstance(self._source, int):
            return self._source
        return self.__fileno__()

    def detach(self):
        self._check_closed()
        self._closed = True
        return self.fileno()

    def flush(self):
        self._check_closed()
        if not isinstance(self._source, int):
            self.__flush__()

    def isatty(self):
        self._check_closed()
        if isinstance(self._source, int):
            return False
        return self.__isatty__()

    def readable(self):
        if isinstance(self._source, int):
            return self._readable
        return self._source.readable()

    def writable(self):
        if isinstance(self._source, int):
            return self._writable
        return self._source.writable()

    def seek(self, *args, **kwargs):
        self._check_seekable()
        self._check_closed()
        if isinstance(self._source, int):
            return 0
        return self._source.seek(*args, **kwargs) if hasattr(self._source, 'seek') else 0

    def seekable(self):
        if isinstance(self._source, int):
            return False
        return self._source.seekable() if hasattr(self._source, 'seekable') else False

    def tell(self):
        self._check_seekable()
        self._check_closed()
        if isinstance(self._source, int):
            return 0
        return self._source.tell() if hasattr(self._source, 'tell') else 0

    def truncate(self, size=None):
        self._check_seekable()
        self._check_closed()
        type_check((size,), (int, None))
        if isinstance(self._source, int):
            return 0
        return self._source.truncate(size) if hasattr(self._source, 'truncate') else 0

    def __repr__(self):
        tp = ''
        if self.readable():
            tp += 'I'
        if self.writable():
            tp += 'O'
        if tp != '':
            tp = ', type=' + tp

        closed = 'closed ' if self._closed else ''
        return f"<{closed}stream '{self._name}' at {hex(id(self))}{tp}>"

    closed = property(lambda self: self._closed)
    name = property(lambda self: self._name)

