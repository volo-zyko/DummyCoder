# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.elements
import dumco.schema.uses

import xsd_base
import xsd_simple_type


def xsd_attribute(attrs, parent_element, factory, schema_path, all_schemata):
    new_element = XsdAttribute(attrs, all_schemata[schema_path], factory)
    parent_element.children.append(new_element)

    factory.add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                                 'attributes')

    return (new_element, {
        'annotation': factory.xsd_annotation,
        'simpleType': xsd_simple_type.xsd_simpleType,
    })


class XsdAttribute(xsd_base.XsdBase):
    def __init__(self, attrs, parent_schema, factory):
        super(XsdAttribute, self).__init__(attrs)

        self.qualified = (
            self.attr('form') == 'qualified' or
            (self.attr('form') != 'unqualified' and
             parent_schema is not None and
             parent_schema.attributes_qualified))

        attribute = dumco.schema.elements.Attribute(
            self.attr('name'), self.attr('default'), self.attr('fixed'),
            parent_schema.schema_element)

        self.schema = parent_schema
        self.schema_element = dumco.schema.uses.AttributeUse(
            self.qualified, attribute.constraint,
            self.attr('use') == 'required', attribute)
        self.prohibited = self.attr('use') == 'prohibited'

    @method_once
    def finalize(self, factory):
        if self.attr('ref') is not None:
            self.schema_element.attribute = \
                factory.resolve_attribute(self.attr('ref'), self.schema)
        elif self.attr('type') is not None:
            self.schema_element.attribute.type = \
                factory.resolve_simple_type(self.attr('type'), self.schema)
        else:
            self.schema_element.attribute.type = \
                dumco.schema.elements.SimpleType.urtype()
            for t in self.children:
                assert isinstance(t, xsd_simple_type.XsdSimpleType), \
                    'Attribute can contain only its type'

                self.schema_element.attribute.type = t.schema_element

        return self.schema_element
