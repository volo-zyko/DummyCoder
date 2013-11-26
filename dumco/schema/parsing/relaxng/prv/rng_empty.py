# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base


def rng_empty(attrs, parent_element, factory, schema_path, all_schemata):
    empty = RngEmpty(attrs, schema_path)

    return (empty, {})


class RngEmpty(rng_base.RngBase):
    def __init__(self, attrs, schema_path):
        super(RngEmpty, self).__init__(attrs)
