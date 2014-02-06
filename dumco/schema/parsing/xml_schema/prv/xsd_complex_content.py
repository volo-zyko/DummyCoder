# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import xsd_base
import xsd_extension_cc
import xsd_restriction_cc


def xsd_complexContent(attrs, parent_element, factory,
                       schema_path, all_schemata):
    new_element = XsdComplexContent(attrs)
    parent_element.children.append(new_element)

    return (new_element, {
        'annotation': factory.noop_handler,
        'extension': xsd_extension_cc.xsd_extension_in_complexContent,
        'restriction': xsd_restriction_cc.xsd_restriction_in_complexContent,
    })


class XsdComplexContent(xsd_base.XsdBase):
    def __init__(self, attrs):
        super(XsdComplexContent, self).__init__(attrs)

        self.mixed = (
            None if self.attr('mixed') is None
            else (self.attr('mixed') == 'true' or self.attr('mixed') == '1'))
        self.part = None
        self.attr_uses = []

    @method_once
    def finalize(self, factory):
        for c in self.children:
            assert (
                (isinstance(c, xsd_extension_cc.XsdComplexExtension) or
                 isinstance(c, xsd_restriction_cc.XsdComplexRestriction)) and
                self.part is None), 'Wrong content of ComplexContent'

            c.finalize(factory)

            self.part = c.part
            self.attr_uses = c.attr_uses

        return self
