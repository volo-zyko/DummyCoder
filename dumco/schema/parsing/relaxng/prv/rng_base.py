# Distributed under the GPLv2 License; see accompanying file COPYING.

import sys


class RngBase(object):
    def __init__(self, attrs, parent):
        self.attrs = attrs
        self.parent = parent
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

    def finalize_children(self, factory):
        pass

    def finalize(self, grammar, all_schemata, factory):
        for c in self.children:
            c.finalize(grammar, all_schemata, factory)

    def dump(self, fhandle, indent): # pragma: no cover
        tag = self.__class__.__name__[3:]
        tag = tag[0].lower() + tag[1:]

        fhandle.write('{}<{}'.format(' ' * indent, tag))

        closing = self._dump_internals(fhandle, indent + 2)

        if closing == 1:
            fhandle.write('/>')
        elif closing == 2:
            fhandle.write('</{}>'.format(tag))
        elif closing == 3:
            fhandle.write('{}</{}>'.format(' ' * indent, tag))
        fhandle.write('\n')

    def _dump_internals(self, fhandle, indent): # pragma: no cover
        res = 1

        if self.text:
            res = 2
            fhandle.write('>{}'.format(self.text))

        if self.children:
            res = 3
            fhandle.write('>\n')
            for c in self.children:
                c.dump(fhandle, indent)

        return res
