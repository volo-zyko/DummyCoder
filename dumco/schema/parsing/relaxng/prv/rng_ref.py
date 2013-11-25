# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base
import rng_element


def rng_ref(attrs, parent_element, factory, schema_path, all_schemata):
    ref = RngRef(attrs, schema_path)

    return (ref, {
        'element': rng_element.rng_element,
        'ref': rng_ref,
    })


class RngRef(rng_base.RngBase):
    def __init__(self, attrs, schema_path):
        super(RngRef, self).__init__(attrs)
