# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.checks
import dumco.schema.model

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

    # Simple restriction is just like the simple type.
    factory.add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                                 'simple_types', is_type=True)

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

        # Should have been named schema_element but it's already defined
        # in the base class.
        self.simple_type = dumco.schema.model.SimpleType(
            None, parent_schema.schema_element)
        self.attr_uses = []

    @method_once
    def finalize(self, factory):
        simple_type = None

        redefined_attr_uses = []
        prohibited_attr_uses = []
        for c in self.children:
            assert (isinstance(c, xsd_simple_type.XsdSimpleType) or
                    isinstance(c, xsd_enumeration.XsdEnumeration) or
                    isinstance(c, xsd_attribute_group.XsdAttributeGroup) or
                    isinstance(c, xsd_attribute.XsdAttribute) or
                    isinstance(c, xsd_any.XsdAny)), \
                'Wrong content of simple Restriction'

            if isinstance(c, xsd_simple_type.XsdSimpleType):
                simple_type = c.finalize(factory)
            elif isinstance(c, xsd_enumeration.XsdEnumeration):
                enum = dumco.schema.model.EnumerationValue(
                    c.value, c.schema_element.doc)
                self.schema_element.enumeration.append(enum)
            elif isinstance(c, xsd_attribute_group.XsdAttributeGroup):
                self.attr_uses.extend(c.finalize(factory).attr_uses)
            elif isinstance(c, xsd_attribute.XsdAttribute):
                if c.prohibited:
                    prohibited_attr_uses.append(c.finalize(factory))
                else:
                    redefined_attr_uses.append(c.finalize(factory))
            elif isinstance(c, xsd_any.XsdAny):
                self.attr_uses.append(c.finalize(factory))

        # Only complex type can be here.
        base = factory.resolve_complex_type(self.attr('base'),
                                            self.schema, finalize=True)

        if simple_type is None:
            base_type = base.text().type
            assert dumco.schema.checks.is_primitive_type(base_type), \
                'Wrong base type of simple Restriction'
        else:
            base_type = simple_type

        self.schema_element.base = self.merge_base_restriction(base_type)

        if dumco.schema.checks.is_complex_type(base):
            self.attr_uses.extend(
                xsd_base.restrict_base_attributes(base, factory,
                                                  prohibited_attr_uses,
                                                  redefined_attr_uses))

        self.attr_uses.extend(redefined_attr_uses)

        self.simple_type.restriction = self.schema_element
        return self.simple_type
