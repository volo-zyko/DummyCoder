# Distributed under the GPLv2 License; see accompanying file COPYING.

import sys

from dumco.utils.decorators import method_once


class RngBase(object):
    def __init__(self):
        super(RngBase, self).__init__()

        self.children = []
        self.text = ''

    def append_text(self, text, builder):
        self.text += text.strip()

    def __setattr__(self, name, value):
        if name not in self.__dict__:
            tb = sys._current_frames().values()[0]
            assert (tb.f_back.f_code.co_name == '__init__' or
                    tb.f_back.f_code.co_filename.endswith('decorators.py')), \
                'Setting non-existent attribute'
        self.__dict__[name] = value

    @method_once
    def finalize(self, grammar, builder):
        del self.children
        del self.text
        return self