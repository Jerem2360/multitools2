"""
Variables used for import manipulation.
"""


__all__ = [
    "__finalizers__",
    "__import_hooks__",
    "__importer_count__",
    "__disabled__",
]


__finalizers__ = {}  # registry for finalizers (functions that execute at the end of a module's runtime)

__import_hooks__ = {}  # registry for import hooks

__importer_count__ = 0  # number of existing importers

__disabled__ = 0  # number of disabled importers

