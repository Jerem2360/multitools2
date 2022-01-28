from . import _meta, _hidden_builtins


def abstract(obj):
    if isinstance(obj, _meta.MultiMeta):
        if not obj.__data__.abstract:
            return _meta.MultiMeta(obj, abstract=True)
        return obj
    res = _meta.FieldWrapper(obj)
    res.__abstract__ = True
    return res

