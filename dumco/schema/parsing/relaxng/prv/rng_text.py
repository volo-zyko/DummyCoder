# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base


def rng_text(attrs, parent_element, factory, schema_path, all_schemata):
    text = RngText(attrs, schema_path)

    return (text, {})


class RngText(rng_base.RngBase):
    def __init__(self, attrs, schema_path):
        super(RngText, self).__init__(attrs)
