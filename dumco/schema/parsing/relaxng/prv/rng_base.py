# Distributed under the GPLv2 License; see accompanying file COPYING.

import sys


class RngBase(object):
    def __init__(self, attrs):
        self.attrs = attrs
        self.children = []
        self.text = ''

    def attr(self, name):
        return self.attrs.get(name, None)

    def append_text(self, text):
        self.text += text.strip()

    def __setattr__(self, name, value):
        if name not in self.__dict__:
            tb = sys._current_frames().values()[0]
            assert tb.f_back.f_code.co_name == '__init__', \
                'Setting non-existent attribute'
        self.__dict__[name] = value
