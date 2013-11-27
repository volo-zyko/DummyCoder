# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base
import rng_except


def rng_anyName(attrs, parent_element, factory, schema_path, all_schemata):
    any_name = RngAnyName(attrs, parent_element, schema_path)
    parent_element.children.append(any_name)

    return (any_name, {
        'except': rng_except.rng_except,
    })


class RngAnyName(rng_base.RngBase):
    def __init__(self, attrs, parent_element, schema_path):
        super(RngAnyName, self).__init__(attrs, parent_element)
