# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.string_utils import quote_xml_string

import base
import utils


def rng_param(attrs, parent_element, builder, grammar_path, all_grammars):
    name = builder.get_attribute(attrs, 'name').strip()

    parent_element.children.append(RngParam(name))

    return (parent_element.children[-1], {})


class RngParam(base.RngBase):
    def __init__(self, name, value=None):
        super(RngParam, self).__init__()

        self.name = name
        self.value = value

    def append_text(self, text, builder):
        self.value = text if self.value is None else self.value + text

    def dump(self, context):
        with utils.RngTagGuard('param', context):
            context.add_attribute('name', self.name)
            context.add_text(quote_xml_string(self.value))
