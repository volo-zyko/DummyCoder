# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.rng_types

import rng_base


def rng_value(attrs, parent_element, factory, schema_path, all_schemata):
    value = RngValue(attrs, schema_path, factory)

    return (value, {})


class RngValue(rng_base.RngBase):
    def __init__(self, attrs, schema_path, factory):
        super(RngValue, self).__init__(attrs)

        self.ns = factory.get_ns()
        self.datatypes_uri = factory.get_datatypes_uri()
        try:
            type_name = factory.get_attribute(attrs, 'type')
            self.type = factory.builtin_types(self.datatypes_uri)[type_name]
        except LookupError:
            self.datatypes_uri = ''
            self.type = dumco.schema.rng_types.rng_builtin_types()['token']
