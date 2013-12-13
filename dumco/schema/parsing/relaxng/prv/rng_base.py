# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import sys


class RngBase(object):
    _CLOSING_EMPTY_TAG = 1
    _CLOSING_TAG_INLINE = 2
    _CLOSING_TAG = 3

    def __init__(self, attrs, parent):
        self.attrs = attrs
        self.parent = parent
        self.children = []
        self.text = ''
        self._tab = 2

    def attr(self, name):
        return self.attrs.get((None, name), None)

    def append_text(self, text):
        self.text += text.strip()

    def __setattr__(self, name, value):
        if name not in self.__dict__:
            tb = sys._current_frames().values()[0]
            assert (tb.f_back.f_code.co_name == '__init__' or
                    tb.f_back.f_code.co_filename.endswith('decorators.py')), \
                'Setting non-existent attribute'
        self.__dict__[name] = value

    @method_once
    def finalize(self, grammar, all_schemata, factory):
        del self.attrs
        del self.children
        del self.text

    def dump(self, fhandle, indent):
        tag = self._tag_name()

        fhandle.write('{}<{}'.format(' ' * indent, tag))

        closing = self._dump_internals(fhandle, indent + self._tab)

        if closing == RngBase._CLOSING_EMPTY_TAG:
            fhandle.write('/>')
        elif closing == RngBase._CLOSING_TAG_INLINE:
            fhandle.write('</{}>'.format(tag))
        elif closing == RngBase._CLOSING_TAG:
            fhandle.write('{}</{}>'.format(' ' * indent, tag))
        fhandle.write('\n')

    def _tag_name(self):
        tag = self.__class__.__name__[3:]
        return tag[0].lower() + tag[1:]

    def _dump_internals(self, fhandle, indent): # pragma: no cover
        assert False, '_dump_internals() should be overriden'
