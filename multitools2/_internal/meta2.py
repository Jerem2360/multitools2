from dataclasses import dataclass

from . import type_check, errors


@dataclass
class _TemplateTypeParameter:
    name: str
    tp: type
    pos: int
    default: object = None

    def __repr__(self):
        return f"<template parameter '{self.name}', type: {self.tp}, default: {self.default}>"


class _TemplateArgumentDescriptor:  # these are stored in the source type's __dict__
    __slots__ = [
        '_owner',
        '_param',
        '_value',
    ]

    def __init__(self, owner, param):
        self._owner = owner
        self._param = param
        self._value = self._param.default

    def assign(self, t_instance):  # t_instance is the template instance (a class!) to assign to
        try:
            value = self._value = t_instance.__template__[self._param.pos]
        except IndexError:
            value = self._param.default
        setattr(t_instance, self._param.name, value)

    def __repr__(self):
        return f"<argument descriptor [{self._param.pos}] '{self._param.name}' of template '{self._owner.__name__}'>"


class _NamespaceRef:
    __slots__ = [
        'namespace',
    ]

    def __init__(self, np):
        self.namespace = np  # keep the namespace alive so __hash__() remains valid

    def __hash__(self):  # to allow key in tree-like structures, found only if same namespace object
        return id(self.namespace)


class MultiMeta(type):
    """__slots__ = [
        '__dict__',
        '__template__',  # template arguments; either 'list' or 'list[_TemplateArgumentDescriptor]'
        '__origin__',  # template type this type came from, or None; 'TemplateType | None'
        '__isabstract__',  # ; 'bool'
        '__isstatic__',  # ; 'bool'
        '__isfinal__',  # ; 'bool'
    ]"""

    _forward_refs: dict[_NamespaceRef, str] = {}


class TemplateType(type):
    """__slots__ = [
        '__dict__',
        '__params__',  # template parameters; 'dict[str, _TemplateTypeParameter]'
        '__args__',  # template argument descriptor names; 'list[str]'
        '__source__',  # source type, as defined by the declaration; 'MultiMeta'
        '_typecache',  # cache for already instantiated types
    ]"""

    @property
    def __isabstract__(cls) -> bool:
        return cls.__source__.__isabstract__

    @__isabstract__.setter
    def __isabstract__(cls, value: bool):
        type_check.parse(bool, value)
        cls.__source__.__isabstract__ = value

    @property
    def __isstatic__(cls) -> bool:
        return cls.__source__.__isstatic__

    @__isstatic__.setter
    def __isstatic__(cls, value: bool):
        type_check.parse(bool, value)
        cls.__source__.__isstatic__ = value

    @property
    def __isfinal__(cls) -> bool:
        return cls.__source__.__isfinal__

    @__isfinal__.setter
    def __isfinal__(cls, value: bool):
        type_check.parse(bool, value)
        cls.__source__.__isfinal__ = value

