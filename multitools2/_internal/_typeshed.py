

MethodWrapper = type((10).__index__)


class _C:
    __slots__ = ['slot']


MemberDescriptor = type(_C.slot)

BuiltinFunction = type(object.__new__)  # static builtin methods / functions

WrapperDescriptor = type(object.__init__)  # builtin slot descriptor

MethodDescriptor = type(object.__dir__)  # builtin method descriptor

GetSetDescriptor = type(int.real)  # builtin get-set ('property') descriptor



