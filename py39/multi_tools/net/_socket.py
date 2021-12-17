from ._bases import SocketBase as _SocketBase
from ._data import User as _User, Address as _Address
from ..errors import *
from socket import fromshare


class Socket:
    """
    Sockets allow multiple machines to communicate together through a network
    or the internet.
    """
    def __init__(self, *args, **kwargs):
        self.__sock = _SocketBase(*args, **kwargs)

    def accept(self):
        """
        Accept a connection from a user while listening.
        """
        accept = self.__sock['accept']
        sock, addr = accept()
        return _User(_Address(*addr), Socket(sock))

    def bind(self):
        """
        Bind the socket to an address.
        Most useful for servers.

        Raises SocketError if socket is already connected.
        """
        self.__sock.bind()

    def close(self):
        """
        Close the connection of the socket.

        Raises SocketError if connection doesn't exist.
        """
        self.__sock.close()

    def connect(self):
        """
        Connect the socket to a distant machine.
        Most useful for clients.

        Raises SocketError if the socket is already connected.
        """
        return self.__sock.connect()

    def detach(self):
        detach = self.__sock['detach']
        return detach()

    def duplicate(self):
        """
        Create and return a copy of self.
        """
        return self

    def listen(self, backlog=None):
        """
        Start listening for connections from distant machines.
        """
        listen = self.__sock['listen']
        args = ()
        if backlog is not None:
            if not isinstance(backlog, int):
                raise SimpleTypeError(type(backlog), 'Optional[int]')
            args = (backlog,)
        listen(*args)

    def share(self, pid):
        """
        Share self with another process, from it's pid and return the data, as bytes.
        """
        if isinstance(pid, int):
            share = self.__sock['share']
            return share(pid)
        raise SimpleTypeError(type(pid), int)

    @staticmethod
    def from_share(info, host):
        """
        Convert a net.Socket.share() data into the actual socket it shares.
        """
        if not isinstance(host, _Address):
            raise SimpleTypeError(type(host), _Address)
        if isinstance(info, bytes):
            return Socket(fromshare(info), host)
        raise SimpleTypeError(type(info), bytes)

    @property
    def fileno(self):
        return self.__sock.fileno

    @property
    def blocking(self):
        getblocking = self.__sock['getblocking']
        return getblocking()

    @blocking.setter
    def blocking(self, value):
        if isinstance(value, bool):
            setblocking = self.__sock['setblocking']
            setblocking(value)
            return
        raise SimpleTypeError(type(value), bool)

    @property
    def timeout(self):
        return self.__sock.timeout

    @timeout.setter
    def timeout(self, value):
        self.__sock.timeout = value

