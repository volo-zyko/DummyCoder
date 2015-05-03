# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.string_utils import quote_xml_string

import base
import utils


def rng_value(attrs, parent_element, builder, grammar_path, all_grammars):
    datatypes_uri = builder.get_datatypes_uri()
    try:
        type_name = builder.get_attribute(attrs, 'type').strip()
        builtin_type = builder.builtin_types(datatypes_uri)[type_name]
    except LookupError:
        datatypes_uri = ''
        builtin_type = builder.builtin_types(None)['token']

    parent_element.children.append(
        RngValue(builder.get_ns(), datatypes_uri, builtin_type))

    return (parent_element.children[-1], {})


class RngValue(base.RngBase):
    def __init__(self, ns, datatypes_uri, builtin_type, value=None):
        super(RngValue, self).__init__()

        self.ns = ns
        self.datatypes_uri = datatypes_uri
        self.type = builtin_type
        self.value = value

    def append_text(self, text, builder):
        self.value = text if self.value is None else self.value + text

    def dump(self, context):
        with utils.RngTagGuard('value', context):
            context.add_attribute('type', self.type.name)
            context.add_attribute('datatypeLibrary', self.datatypes_uri)
            context.add_attribute('ns', self.ns)
            context.add_text(quote_xml_string(self.value))
