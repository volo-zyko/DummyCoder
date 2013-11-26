# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base
import rng_except
import rng_param


def rng_data(attrs, parent_element, factory, schema_path, all_schemata):
    data = RngData(attrs, schema_path, factory)

    return (data, {
        'param': rng_param.rng_param,
        'except': rng_except.rng_except,
    })


class RngData(rng_base.RngBase):
    def __init__(self, attrs, schema_path, factory):
        super(RngData, self).__init__(attrs)

        self.datatypes_uri = factory.get_datatypes_uri()
        type_name = factory.get_attribute(attrs, 'type')
        self.type = factory.builtin_types(self.datatypes_uri)[type_name]
