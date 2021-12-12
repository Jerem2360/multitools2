from .._multi_class import MultiMeta as _MultiMeta, AbstractMethodDescriptor as _abstractmethod


class Stream(metaclass=_MultiMeta):
    @_abstractmethod
    def __gethandle__(self):
        pass

    @property
    def handle(self):
        return self.__gethandle__()

    @property
    def readable(self):
        return hasattr(self, "_readable")

    @property
    def writable(self):
        return hasattr(self, "_writable")


class OStream(Stream, metaclass=_MultiMeta):
    _writable = True

    @_abstractmethod
    def __write__(self, data, **kwargs):
        pass

    def write(self, data, **kwargs):
        return self.__write__(data, **kwargs)


class IStream(Stream, metaclass=_MultiMeta):
    _readable = True

    @_abstractmethod
    def __read__(self, size, **kwargs):
        pass

    def read(self, size, **kwargs):
        return self.__read__(size, **kwargs)

    def readline(self, **kwargs):
        pass

