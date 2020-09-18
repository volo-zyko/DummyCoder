# Distributed under the GPLv2 License; see accompanying file COPYING.

import inspect


class XsdBase(object):
    def __init__(self, attrs):
        self.attrs = attrs
        self.children = []

    def attr(self, name):
        return self.attrs.get(name, None)

    def __setattr__(self, name, value):
        if name not in self.__dict__:
            frame = inspect.currentframe().f_back
            assert (frame.f_code.co_name == '__init__' or
                    frame.f_code.co_filename.endswith('decorators.py')), \
                'Setting non-existent attribute'
        self.__dict__[name] = value
