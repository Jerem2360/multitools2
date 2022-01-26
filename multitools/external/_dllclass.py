from .._decorator import *
from ._library import *
from .._meta import *


@Decorator
def DllClass(cls, path, flags=0):
    cls.__source__ = Library.load(path, flags)

