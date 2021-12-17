from py39.multi_tools.io import Stream as _Stream
from ._data import Package as _Package, Address as _Address
from ..errors import *
import socket
from _socket import gaierror
from ..functional import Failure as _Failure, Success as _Success


class SocketBase(_Stream[_Package]):
    def __init__(self, arg1, *args, **kwargs):
        """
        The base class for multi_tools.net sockets.
        Represents the stream of the socket.

        Different ways to initialize the class:

        - with an existing socket.socket object, providing the host of it:
        SocketBase(sock: socket.socket, host: net.Address) -> Socket Stream

        - from scratch providing a host, and eventually family, type and protocol:
        SocketBase(host: net.Address, family: int = ..., type_: int = ..., proto: int = ...) -> Socket Stream

        """
        self.__connected = False

        if isinstance(arg1, socket.socket):
            super().__init__(arg1, _Package, read='recv', write='send')

            if len(args) == 1:
                h = args[0]
                if isinstance(h, _Address):
                    self.__host = h
                    if self._try_send():
                        self.__connected = True

                    return
                raise SimpleTypeError(type(h), _Address)

            elif len(args) == 0:
                raise ValueError("SocketBase.__init__() missing 1 required positional argument 'host'.")
            raise ValueError(f"SocketBase.__init__() takes only 2 positional arguments, but {len(args) + 1} were given.")

        if isinstance(arg1, _Address):

            family = -1
            if 'family' in kwargs:
                f = kwargs.get('family')
                if isinstance(f, int):
                    family = f
                else:
                    raise SimpleTypeError(type(f), int)

            type_ = -1
            if 'type_' in kwargs:
                t = kwargs.get('type_')
                if isinstance(t, int):
                    type_ = t
                else:
                    raise SimpleTypeError(type(t), int)

            proto = -1
            if 'proto' in kwargs:
                p = kwargs.get('proto')
                if isinstance(p, int):
                    proto = p
                else:
                    raise SimpleTypeError(type(p), int)

            s = socket.socket(family=family, type=type_, proto=proto)
            super().__init__(s, _Package, read='recv', write='send')
            self.__host = arg1

    def _try_send(self):
        try:
            self.handle.send(b"")
        except gaierror:
            return _Failure(*sys.exc_info())
        return _Success()

    def connect(self):
        """
        Connect to self.address
        Most useful for clients.

        raises SocketError if socket is already connected.
        """
        if not self.__connected:
            address = self.__host.address
            port = self.__host.port
            res = self.handle.connect_ex((address, port))
            self.__connected = True
            return res
        raise SocketError("Socket is already connected!")

    def bind(self):
        """
        Bind to self.address
        Most useful for servers.

        raises SocketError if socket is already connected.
        """
        address = self.__host.address
        port = self.__host.port
        res = self.handle.bind((address, port))
        self.__connected = True
        return res

    def close(self):
        """
        Close connection to self.address

        raises SocketError if socket is not connected.
        """
        if self.__connected:
            self.__connected = False
            return
        raise SocketError("Socket is not connected.")

    def __write__(self, data, flush=False, flags=None):
        if isinstance(data, _Package):
            return super().__write__(data.data, flush=False, flags=flags)
        raise SimpleTypeError(type(data), _Package)

    def __writable__(self):
        return self.__connected

    def __read__(self, size):
        if isinstance(size, int):
            data = super().__read__(size)
            return _Package(data)
        raise SimpleTypeError(type(size), int)

    def __readable__(self):
        return self.__connected

    def __getitem__(self, item):
        if isinstance(item, str):
            try:
                res = getattr(self.handle, item)
            except AttributeError:
                raise
            return res
        raise SimpleTypeError(type(item), str)

    @property
    def timeout(self):
        """
        Time after which TimeoutError is raised when no response.
        """
        return self.handle.gettimeout()

    @timeout.setter
    def timeout(self, value):
        if isinstance(value, (float, type(None))):
            self.handle.settimeout(value)
            return
        raise SimpleTypeError(type(value), 'Optional[float]')

    @property
    def address(self):
        """
        The address to which the socket is linked, in form of a
        net.Address object.
        """
        return self.__host

    @property
    def connected(self):
        """
        Whether the socket is connected or not.
        """
        return self.__connected

