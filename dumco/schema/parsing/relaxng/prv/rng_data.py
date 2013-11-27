# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base
import rng_except
import rng_param


def rng_data(attrs, parent_element, factory, schema_path, all_schemata):
    data = RngData(attrs, parent_element, schema_path, factory)
    parent_element.children.append(data)

    return (data, {
        'param': rng_param.rng_param,
        'except': rng_except.rng_except,
    })


class RngData(rng_base.RngBase):
    def __init__(self, attrs, parent_element, schema_path, factory):
        super(RngData, self).__init__(attrs, parent_element)

        self.datatypes_uri = factory.get_datatypes_uri()
        type_name = factory.get_attribute(attrs, 'type')
        self.type = factory.builtin_types(self.datatypes_uri)[type_name]

    def _dump_internals(self, fhandle, indent): # pragma: no cover
        fhandle.write(' type="{}" datatypeLibrary="{}"'.
                      format(self.type.name, self.datatypes_uri))
        return super(RngData, self)._dump_internals(fhandle, indent)
