# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base


def rng_name(attrs, parent_element, factory, grammar_path, all_grammars):
    name = RngName(attrs, '', factory)
    parent_element.children.append(name)

    return (name, {})


class RngName(rng_base.RngBase):
    def __init__(self, attrs, text, factory):
        super(RngName, self).__init__(attrs)

        (ns, name) = factory.parse_qname(text)
        self.ns = factory.get_ns() if ns is None else ns
        self.name = None if name == '' else name

        # Temporary for append_text().
        self.factory = factory

        # It's necessary for conversion to XSD.
        self.qualified = self._is_qualified(ns)

    def append_text(self, text):
        assert self.name is None, \
            'Name is defined as both attribute and name class'

        (ns, name) = self.factory.parse_qname(text.strip())
        if name != '':
            self.name = name
        if ns is not None:
            self.ns = ns

        self.qualified = self._is_qualified(ns)

    def _is_qualified(self, ns):
        if ns is not None:
            return ns != ''

        return self.factory.get_ns() != ''

    def _dump_internals(self, fhandle, indent):
        fhandle.write(' ns="{}">{}'.format(self.ns, self.name))
        return rng_base.RngBase._CLOSING_TAG_INLINE
