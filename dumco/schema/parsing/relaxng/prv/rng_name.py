# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base


def rng_name(attrs, parent_element, factory, grammar_path, all_grammars):
    name = RngName(attrs, '', factory)
    parent_element.children.append(name)

    return (name, {})


class RngName(rng_base.RngBase):
    def __init__(self, attrs, text, factory):
        super(RngName, self).__init__(attrs)

        (ns, self.name) = factory.parse_qname(text)
        self.ns = factory.get_ns() if ns is None else ns

        # Temporary for append_text().
        self.factory = factory

    def append_text(self, text):
        (ns, name) = self.factory.parse_qname(text.strip())
        if name != '':
            self.name = name if self.name is None else self.name + name
        if ns is not None:
            self.ns = ns

    def _dump_internals(self, fhandle, indent):
        fhandle.write(' ns="{}">{}'.format(self.ns, self.name))
        return rng_base.RngBase._CLOSING_TAG_INLINE
