# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.rng_types

import rng_base


def rng_value(attrs, parent_element, factory, grammar_path, all_grammars):
    value = RngValue(attrs, parent_element, grammar_path, factory)
    parent_element.children.append(value)

    return (value, {})


class RngValue(rng_base.RngBase):
    def __init__(self, attrs, parent_element, grammar_path, factory):
        super(RngValue, self).__init__(attrs, parent_element)

        self.ns = factory.get_ns()
        self.datatypes_uri = factory.get_datatypes_uri()
        try:
            type_name = factory.get_attribute(attrs, 'type').strip()
            self.type = factory.builtin_types(self.datatypes_uri)[type_name]
        except LookupError:
            self.datatypes_uri = ''
            self.type = dumco.schema.rng_types.rng_builtin_types()['token']

    def append_text(self, text):
        self.text += text

    def _dump_internals(self, fhandle, indent): # pragma: no cover
        fhandle.write(' type="{}" datatypeLibrary="{}" ns="{}"'.
                      format(self.type.name, self.datatypes_uri, self.ns))
        return super(RngValue, self)._dump_internals(fhandle, indent)
