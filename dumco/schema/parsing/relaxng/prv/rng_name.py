# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base


def rng_name(attrs, parent_element, factory, schema_path, all_schemata):
    name = RngName(attrs, parent_element, schema_path, factory)
    parent_element.children.append(name)

    return (name, {})


class RngName(rng_base.RngBase):
    def __init__(self, attrs, parent_element, schema_path, factory):
        super(RngName, self).__init__(attrs, parent_element)

        (self.ns, self.name) = factory.parse_qname(self.text)
        self.ns = factory.get_ns() if self.ns is None else self.ns

    def _dump_internals(self, fhandle, indent): # pragma: no cover
        fhandle.write(' ns="{}"'.format(self.ns))
        return super(RngName, self)._dump_internals(fhandle, indent)
