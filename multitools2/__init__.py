from ._meta import *


class TestParent(metaclass=MultiMeta):
    __fields__ = [
        "contents",
    ]

    def __init__(self, data):
        print(data)

    def set_contents(self, value): ...


# TestParent = MultiMeta(TestParent, abstract=True)


class Test(TestParent, metaclass=MultiMeta):
    pass

