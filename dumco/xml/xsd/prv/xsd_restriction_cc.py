# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.base
import dumco.schema.checks

import xsd_all
import xsd_any
import xsd_attribute
import xsd_attribute_group
import xsd_base
import xsd_choice
import xsd_group
import xsd_sequence


def xsd_restriction_in_complexContent(attrs, parent_element, factory,
                                      schema_path, all_schemata):
    new_element = XsdComplexRestriction(attrs)
    parent_element.children.append(new_element)

    return (new_element, {
        'all': xsd_all.xsd_all,
        'annotation': factory.noop_handler,
        'anyAttribute': xsd_any.xsd_anyAttribute,
        'attribute': xsd_attribute.xsd_attribute,
        'attributeGroup': xsd_attribute_group.xsd_attributeGroup,
        'choice': xsd_choice.xsd_choice,
        'group': xsd_group.xsd_group,
        'sequence': xsd_sequence.xsd_sequence,
    })


class XsdComplexRestriction(xsd_base.XsdBase):
    def __init__(self, attrs):
        super(XsdComplexRestriction, self).__init__(attrs)

        self.particle = None
        self.attributes = []

    @method_once
    def finalize(self, factory):
        for c in self.children:
            if (isinstance(c, xsd_all.XsdAll) or
                isinstance(c, xsd_choice.XsdChoice) or
                isinstance(c, xsd_sequence.XsdSequence) or
                isinstance(c, xsd_group.XsdGroup)):
                assert self.particle is None, 'Content model overriden'
                self.particle = c.finalize(factory)
            elif isinstance(c, xsd_attribute_group.XsdAttributeGroup):
                c.finalize(factory)
                self.attributes.extend(c.attributes)
            elif (isinstance(c, xsd_attribute.XsdAttribute) or
                  isinstance(c, xsd_any.XsdAny)):
                self.attributes.append(c.finalize(factory))
            else: # pragma: no cover
                assert False, 'Wrong content of complex Restriction'

        return self
