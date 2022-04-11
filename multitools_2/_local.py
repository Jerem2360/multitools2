

def customPath(value):
    def _wrap(x):
        x.__module__ = value
        return x
    return _wrap

