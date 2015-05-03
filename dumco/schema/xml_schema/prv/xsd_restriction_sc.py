# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.checks
import dumco.schema.model

import base
import utils
import xsd_any_attribute
import xsd_attribute
import xsd_attribute_group
import xsd_enumeration
import xsd_simple_type


def xsd_restriction(attrs, parent, builder, schema_path, all_schemata):
    base_name = builder.get_attribute(attrs, 'base', default='')
    base_name = builder.parse_qname(base_name)

    new_element = XsdSimpleRestriction(base_name,
                                       parent_schema=all_schemata[schema_path])
    parent.children.append(new_element)

    # Simple restriction is just like the simple type.
    builder.add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                                 'simple_types', is_type=True)

    return (new_element, {
        'annotation': builder.noop_handler,
        'anyAttribute': xsd_any_attribute.xsd_anyAttribute,
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


class XsdSimpleRestriction(base.XsdRestrictionBase):
    def __init__(self, base_name, parent_schema=None):
        super(XsdSimpleRestriction, self).__init__()

        self.base_name = base_name
        self.parent_schema = parent_schema
        self.dom_element = dumco.schema.model.Restriction()

    @method_once
    def finalize(self, builder):
        base_type = dumco.schema.model.SimpleType(
            None, self.parent_schema.dom_element)
        attr_uses = []

        local_simple_type = None
        redefined_attr_uses = []
        prohibited_attr_uses = []
        for c in self.children:
            assert (isinstance(c, xsd_simple_type.XsdSimpleType) or
                    isinstance(c, xsd_enumeration.XsdEnumeration) or
                    isinstance(c, xsd_attribute_group.XsdAttributeGroup) or
                    isinstance(c, xsd_attribute.XsdAttribute) or
                    isinstance(c, xsd_any_attribute.XsdAnyAttribute)), \
                'Wrong content of simple Restriction'

            if isinstance(c, xsd_simple_type.XsdSimpleType):
                local_simple_type = c.finalize(builder)
            elif isinstance(c, xsd_enumeration.XsdEnumeration):
                enum = dumco.schema.model.EnumerationValue(c.value,
                                                           ' '.join(c.text))
                self.dom_element.enumerations.append(enum)
            elif isinstance(c, xsd_attribute_group.XsdAttributeGroup):
                attr_uses.extend(c.finalize(builder))
            elif isinstance(c, xsd_attribute.XsdAttribute):
                if c.prohibited:
                    prohibited_attr_uses.append(c.finalize(builder))
                else:
                    redefined_attr_uses.append(c.finalize(builder))
            elif isinstance(c, xsd_any_attribute.XsdAnyAttribute):
                attr_uses.append(c.finalize(builder))

        # Only complex type can be here. That's the essence of restriction.
        base_ct = builder.resolve_complex_type(self.base_name,
                                               self.parent_schema)

        if dumco.schema.checks.is_complex_type(base_ct):
            attr_uses.extend(
                utils.restrict_base_attributes(base_ct, builder,
                                               prohibited_attr_uses,
                                               redefined_attr_uses))

        attr_uses.extend(redefined_attr_uses)

        if local_simple_type is None:
            base_st = base_ct.text().type
            assert dumco.schema.checks.is_primitive_type(base_st), \
                'Simple Restriction must restrict only Simple Content'
        else:
            base_st = local_simple_type

        restriction_or_type = utils.connect_restriction_base(self.dom_element,
                                                             base_st)

        if dumco.schema.checks.is_restriction(restriction_or_type):
            base_type.restriction = restriction_or_type
        else:
            base_type = restriction_or_type

        base_type = utils.eliminate_degenerate_simple_type(base_type)

        return (base_type, attr_uses)
