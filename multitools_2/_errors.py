import sys


def _NoPath(error):
    error.__module__ = "builtins"
    return error


def latest():
    return sys.exc_info()[0](*sys.exc_info()[1].args)


@_NoPath
class ExternalReferenceError(ImportError):
    def __init__(self, *args, source=None, wrong_ref=None):
        if (source is None) or (wrong_ref is None):
            super().__init__(*args)
            return
        if len(args) > 0:
            super().__init__(*(str(arg).format(source, wrong_ref) for arg in args))
            return
        super().__init__(f"Failed to resolve external reference '{wrong_ref}' for '{source}' object.")

