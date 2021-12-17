import types
import sys


class ContextError(BaseException):

    pass


class SocketError(BaseException):
    def __init__(self, *args):
        super().__init__(*args)


def SimpleTypeError(got: type, *expected, source: str = None):
    if len(expected) == 0:
        expected = (type(None),)

    typeset = set(expected)
    expected = list(typeset)

    if isinstance(expected[0], type):
        expected_text = expected[0].__name__
    else:
        expected_text = expected[0]

    expected.pop(0)
    for type_ in expected:
        if isinstance(type_, type):
            name = type_.__name__
        else:
            name = type_

        expected_text += " or "
        expected_text += f"'{name}'"

    got_str = got.__name__
    final = f"Expected type {expected_text}, got '{got_str}' instead."
    if source is not None:
        final = f"'{source}': " + final

    return TypeError(final)

