

__all__ = [
    "Function",
]

def f(): ...
Function = type(f)
del f

