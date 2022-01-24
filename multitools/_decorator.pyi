from types import FunctionType
from ._meta import *


class Decorator(metaclass=MultiMeta):
    def __new__(cls, function: FunctionType) -> FunctionType: ...

