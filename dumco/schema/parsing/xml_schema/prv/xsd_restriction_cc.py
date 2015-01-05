# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import utils
import xsd_all
import xsd_any
import xsd_attribute
import xsd_attribute_group
import xsd_choice
import xsd_group
import xsd_sequence


def xsd_restriction_in_complexContent(attrs, parent_element, factory,
                                      schema_path, all_schemata):
    new_element = XsdComplexRestriction(attrs, all_schemata[schema_path])
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


class XsdComplexRestriction(base.XsdBase):
    def __init__(self, attrs, parent_schema):
        super(XsdComplexRestriction, self).__init__(attrs)

        self.schema = parent_schema
        self.part = None
        self.attr_uses = []

    @method_once
    def finalize(self, factory):
        redefined_attr_uses = []
        prohibited_attr_uses = []
        for c in self.children:
            if (isinstance(c, xsd_all.XsdAll) or
                    isinstance(c, xsd_choice.XsdChoice) or
                    isinstance(c, xsd_sequence.XsdSequence) or
                    isinstance(c, xsd_group.XsdGroup)):
                assert self.part is None, 'Content model overridden'
                self.part = c.finalize(factory)
            elif isinstance(c, xsd_attribute_group.XsdAttributeGroup):
                self.attr_uses.extend(c.finalize(factory).attr_uses)
            elif isinstance(c, xsd_attribute.XsdAttribute):
                if c.prohibited:
                    prohibited_attr_uses.append(c.finalize(factory))
                else:
                    redefined_attr_uses.append(c.finalize(factory))
            elif isinstance(c, xsd_any.XsdAny):
                self.attr_uses.append(c.finalize(factory))
            else:  # pragma: no cover
                assert False, 'Wrong content of complex Restriction'

        base_ct = factory.resolve_complex_type(self.attr('base'), self.schema)

        self.attr_uses.extend(
            utils.restrict_base_attributes(base_ct, factory,
                                           prohibited_attr_uses,
                                           redefined_attr_uses))

        self.attr_uses.extend(redefined_attr_uses)

        return self
