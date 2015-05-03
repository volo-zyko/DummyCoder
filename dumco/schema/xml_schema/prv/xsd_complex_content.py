# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import xsd_extension_cc
import xsd_restriction_cc


def xsd_complexContent(attrs, parent, builder, schema_path, all_schemata):
    mixed = builder.get_attribute(attrs, 'mixed', default=None)
    mixed = (None if mixed is None
             else (mixed == 'true' or mixed == '1'))

    new_element = XsdComplexContent(mixed)
    parent.children.append(new_element)

    return (new_element, {
        'annotation': builder.noop_handler,
        'extension': xsd_extension_cc.xsd_extension,
        'restriction': xsd_restriction_cc.xsd_restriction,
    })


class XsdComplexContent(base.XsdBase):
    def __init__(self, mixed):
        super(XsdComplexContent, self).__init__()

        self.mixed = mixed

    @method_once
    def finalize(self, builder):
        part = None
        attr_uses = []

        for c in self.children:
            assert (
                (isinstance(c, xsd_extension_cc.XsdComplexExtension) or
                 isinstance(c, xsd_restriction_cc.XsdComplexRestriction)) and
                part is None and not attr_uses), \
                'Wrong content of ComplexContent'

            (part, attr_uses) = c.finalize(builder)

        return (part, attr_uses)
