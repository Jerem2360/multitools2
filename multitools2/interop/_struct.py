from ._basis import *


class StructureField:
    """
    Represents structure instance fields.
    """
    def __init__(self, offset, tp):
        type_check.parse(SupportsIndex, ForeignData_Meta, offset, tp)
        offset = offset.__index__()

        self._offset = offset
        self._type = tp
        self._name = None

    def __get__(self, instance, owner):
        """
        Return the value of a structure's field.
        """
        if instance is None:
            return self
        if not issubclass(owner, Structure):
            return self

        type_check.parse(Structure, Structure_Type, instance, owner)

        mem = memory.Memory(instance.__memory__.view()[self._offset:self._offset+self._type.__size__])
        obj = self._type.__new__(self._type)
        obj.__memory__ = mem
        return obj

    def __set__(self, instance, value):
        """
        Set the value of a structure's field.
        """
        if not isinstance(instance, Structure):
            if self._name is not None:
                setattr(instance, self._name, value)
            return

        if not isinstance(value, self._type):
            # here, we treat value as an initializer
            if isinstance(value, tuple):
                value = value
            elif isinstance(value, list):
                value = tuple(value)
            else:
                value = (value,)
            with errors.frame_mask:
                value = self._type(*value)
        src_mem = value.__memory__
        instance.__memory__[self._offset:self._offset+self._type.__size__] = src_mem[:]

    def __set_name__(self, owner, name):
        """
        Set the name of the field we're assigned to.
        """
        # print(f"setting name of {self} to {repr(name)}.")
        self._name = name

    def __repr__(self):
        if self._name is None:
            return f"<Structure member, type: '{self._type.__name__}', offset={self._offset}>"
        return f"<Member '{self._name}', type: '{self._type.__name__}', offset={self._offset}>"


class Structure_Type(ForeignData_Meta):
    """
    Base metatype for structure types.
    """

    def __new__(mcs, name, bases, np, **kwargs):
        from .._internal import meta
        struct_type = ""
        size = 0
        largest = 0
        np['_incomplete'] = False

        # allow to disable field padding:
        padding = kwargs.get('padding', True)

        annotations = np.get('__annotations__', {})
        fields = {}

        field_types = {}

        for k, v in annotations.items():
            if isinstance(v, str):
                raise NotImplementedError("Forward references are not supported.") from errors.configure(depth=1)

            if k in np:
                # we do not want to override assigned fields
                continue
            if issubclass(v, ForeignData):
                if padding and not issubclass(v, Structure):
                    if size % v.__size__:
                        diff = v.__size__ - (size % v.__size__)
                        size += diff

                    largest = max(largest, v.__size__)

                fields[k] = size
                field_types[k] = v
                struct_type += v.__struct_type__

                np[k] = StructureField(size, v)
                size += v.__size__

        if padding and largest and (size % largest):
            diff = largest - (size % largest)
            size += diff

        with errors.frame_mask:
            res = ForeignData_Meta.__new__(mcs, name, bases, np, size=size, struct_type=struct_type)
        res.__fields__ = fields
        res.__field_types__ = field_types

        return res

    @property
    def __forward_refs__(cls):
        res = []
        for k, v in cls.__field_types__.items():
            res.extend(v.__forward_refs__)
        return res


@abstract
class Structure(ForeignData, metaclass=Structure_Type):
    """
    Base class for structure types.
    Structures hold nothing but the chunk of memory where their
    data is stored.
    Accessing their fields will fetch the correct chunk of memory
    and make a ForeignData instance out of it. During the process,
    no data is copied. This returns a new ForeignData instance each
    time.


    Default implementation for as_object() returns a tuple
    of field.as_object() for each field.

    e.g.

    class C(Structure):

        f1: Int
        f2: LongLong


    class D(Structure):

        c1: C
        c2: C


    c1 = C()  # all fields are initialized to 0
    c2 = C(14, 15)  # f1 is set to Int(14) and f2 is set to LongLong(15).

    d1 = D()  # all fields are initialized to 0
    d2 = D((1, 2), c2)  # D.c1 is set to C(1, 2) and D.c2 is set to c2

    >> c1.as_object()
    (0, 0)
    >> c2.as_object()
    (14, 15)

    >> c1.f1 = 10  # this sets c1.f1 to Int(10)
    >> c1.as_object()
    (10, 0)
    >> c1.f1.as_object()
    10

    # actual instances can be used in place of initializers:

    >> c1.f2 = LongLong(144)
    >> c1.f2.as_object()
    144
    """
    def __init__(self, *members):
        """
        Initialize a new structure variable.
        Fields are given values depending on the parameters.

        Parameters may be initializers for their type.
        """

        i = -1
        for k in self.__fields__:
            i += 1
            t = getattr(type(self), k)._type
            if i >= len(members):
                continue
            if isinstance(members[i], t):
                setattr(self, k, members[i])
                continue

            if isinstance(members[i], tuple):
                initializer = members[i]
            elif isinstance(members[i], list):
                initializer = tuple(members[i])
            else:
                initializer = (members[i],)

            with errors.frame_mask:
                setattr(self, k, t(*initializer))
