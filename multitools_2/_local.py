

def customPath(value):
    def _wrap(x):
        x.__module__ = value
        return x
    return _wrap


def noPath(func):
    return customPath("builtins")(func)


def customName(name):
    def _wrap(x):
        x.__name__ = name
        x.__qualname__ = name
        return x
    return _wrap

