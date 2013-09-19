# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.checks

import xsd_any
import xsd_attribute
import xsd_attribute_group
import xsd_base
import xsd_enumeration
import xsd_restriction
import xsd_simple_type


def xsd_restriction_in_simpleContent(attrs, parent_element, factory,
                                     schema_path, all_schemata):
    new_element = XsdSimpleRestriction(attrs, all_schemata[schema_path])
    parent_element.children.append(new_element)

    return (new_element, {
        'annotation': factory.noop_handler,
        'anyAttribute': xsd_any.xsd_anyAttribute,
        'attribute': xsd_attribute.xsd_attribute,
        'attributeGroup': xsd_attribute_group.xsd_attributeGroup,
        'enumeration': xsd_enumeration.xsd_enumeration,
        'fractionDigits': new_element.xsd_fractionDigits,
        'length': new_element.xsd_length,
        'maxExclusive': new_element.xsd_maxExclusive,
        'maxInclusive': new_element.xsd_maxInclusive,
        'maxLength': new_element.xsd_maxLength,
        'minExclusive': new_element.xsd_minExclusive,
        'minInclusive': new_element.xsd_minInclusive,
        'minLength': new_element.xsd_minLength,
        'pattern': new_element.xsd_pattern,
        'simpleType': xsd_simple_type.xsd_simpleType,
        'totalDigits': new_element.xsd_totalDigits,
        'whiteSpace': new_element.xsd_whiteSpace,
    })


class XsdSimpleRestriction(xsd_restriction.XsdRestriction):
    def __init__(self, attrs, parent_schema):
        super(XsdSimpleRestriction, self).__init__(attrs, parent_schema)

        self.base = None
        self.attributes = []

    @method_once
    def finalize(self, factory):
        for c in self.children:
            assert (isinstance(c, xsd_simple_type.XsdSimpleType) or
                    isinstance(c, xsd_enumeration.XsdEnumeration) or
                    isinstance(c, xsd_attribute_group.XsdAttributeGroup) or
                    isinstance(c, xsd_attribute.XsdAttribute) or
                    isinstance(c, xsd_any.XsdAny)), \
                'Wrong content of simple Restriction'

            if isinstance(c, xsd_simple_type.XsdSimpleType):
                # self.schema_element is declared in base class.
                self.schema_element.base = c.schema_element
            elif isinstance(c, xsd_attribute_group.XsdAttributeGroup):
                c.finalize(factory)
                self.attributes.extend(c.attributes)
            elif (isinstance(c, xsd_attribute.XsdAttribute) or
                  isinstance(c, xsd_any.XsdAny)):
                self.attributes.append(c.finalize(factory))

        if self.schema_element.base is None and self.attr('base') is not None:
            base = factory.resolve_type(self.attr('base'),
                                        self.schema, finalize=True)

            assert ((dumco.schema.checks.is_complex_type(base) and
                     dumco.schema.checks.has_simple_content(base)) or
                    dumco.schema.checks.is_primitive_type(base)), \
                'Wrong base type of simple Restriction'

            if (dumco.schema.checks.is_complex_type(base) and
                dumco.schema.checks.has_simple_content(base)):
                self.schema_element.base = base.text.type

        super(XsdSimpleRestriction, self).finalize(factory)
        self.base = self.schema_element.base
        return self
