# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base


def rng_param(attrs, parent_element, factory, grammar_path, all_grammars):
    param = RngParam(attrs, parent_element)
    parent_element.children.append(param)

    return (param, {})


class RngParam(rng_base.RngBase):
    def __init__(self, attrs, parent_element):
        super(RngParam, self).__init__(attrs, parent_element)

        self.name = self.attr('name').strip()
        self.value = None

    def append_text(self, text):
        self.value = text if self.value is None else self.value + text

    def _dump_internals(self, fhandle, indent):
        fhandle.write(' name="{}">{}'.format(self.name, self.value))
        return rng_base.RngBase._CLOSING_TAG_INLINE
