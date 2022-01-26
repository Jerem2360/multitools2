import types


class CustomException(BaseException):
    def __new__(cls, module, base, *args, **kwargs):
        if (not issubclass(base, BaseException)) and (base is not BaseException):
            return BaseException("<no details>")
        error = type(cls.__name__, (base,), {})
        if isinstance(module, str):
            error.__module__ = module
        elif isinstance(module, types.ModuleType):
            error.__module__ = module.__name__
        else:
            error.__module__ = '<unreachable>'

        return error(*args, **kwargs)

