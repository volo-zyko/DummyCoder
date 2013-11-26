# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base


def rng_param(attrs, parent_element, factory, schema_path, all_schemata):
    param = RngParam(attrs, schema_path, factory)

    return (param, {})


class RngParam(rng_base.RngBase):
    def __init__(self, attrs, schema_path, factory):
        super(RngParam, self).__init__(attrs)

        self.name = factory.get_attribute(attrs,  'name')
