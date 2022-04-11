

class Constant:
    def __init__(self, x):
        self._x = x

    def __get__(self, instance, owner):
        return self._x

    def __set__(self, instance, value):
        raise ValueError("readonly.")

