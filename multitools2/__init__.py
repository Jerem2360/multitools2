from ._meta import *


class Test(metaclass=MultiMeta):
    __fields__ = [
        "contents",
        "shit",
    ]

    contents = "coucou"

    def __new__(cls, *args, **kwargs):
        print("new test")
        return super().__new__(cls)

    def __init__(self, shit="merde"):
        self.shit = shit


#Test = MultiMeta(Test, abstract=True)

