# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base


def rng_name(attrs, parent_element, factory, schema_path, all_schemata):
    name = RngName(attrs, schema_path)

    return (name, {})


class RngName(rng_base.RngBase):
    def __init__(self, attrs, schema_path):
        super(RngName, self).__init__(attrs)
