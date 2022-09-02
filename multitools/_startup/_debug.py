"""
Support for internal debugging.
"""


import sys

__do_debug__ = False
__debug_channels__ = [None]


class debugger:
    """
    A debugging channel.
    Allows finer control on what stuff to debug or not.
    """
    def __init__(self, channel=None):
        self._channel = channel

    def print(self, *values, sep=None, end='\n', file=sys.stdout, flush=False):
        if __do_debug__ and (self._channel in __debug_channels__):
            channel = 'MAIN/debug' if self._channel is None else self._channel
            print(f"[{channel}]", *values, sep=sep, end=end, file=file, flush=flush)

    @classmethod
    def audit(cls, name, *args):
        sys.audit(name, *args)

    channel = property(lambda self: self._channel)

