

__all__ = [
    "Function",
    "Method"
]

def f(): ...
Function = type(f)
del f


class C:
    def f(self): ...

Method = type(C().f)

del C

