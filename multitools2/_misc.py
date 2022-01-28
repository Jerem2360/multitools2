

class SimpleMeta(type):
    def __repr__(cls):
        return f"<multitools class '{cls.__name__}'>"


class GetSetDict(dict, metaclass=SimpleMeta):
    def __getattr__(self, item):
        return super().__getitem__(item)

    def __setattr__(self, key, value):
        return super().__setitem__(key, value)

