# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base
import rng_element


def rng_ref(attrs, parent_element, factory, schema_path, all_schemata):
    ref = RngRef(attrs, parent_element, schema_path, factory)
    parent_element.children.append(ref)

    return (ref, {
        'element': rng_element.rng_element,
        'ref': rng_ref,
    })


class RngRef(rng_base.RngBase):
    def __init__(self, attrs, parent_element, schema_path, factory):
        super(RngRef, self).__init__(attrs, parent_element)

        self.name = factory.get_attribute(attrs,  'name')

    def _dump_internals(self, fhandle, indent): # pragma: no cover
        fhandle.write(' name="{}"'.format(self.name))
        return super(RngRef, self)._dump_internals(fhandle, indent)
