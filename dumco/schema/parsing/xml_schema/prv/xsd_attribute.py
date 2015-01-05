# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.model
import dumco.schema.uses
import dumco.schema.xsd_types

import base
import xsd_schema
import xsd_simple_type


def xsd_attribute(attrs, parent_element, factory, schema_path, all_schemata):
    new_element = XsdAttribute(attrs, parent_element,
                               all_schemata[schema_path], factory)
    parent_element.children.append(new_element)

    factory.add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                                 'attributes')

    return (new_element, {
        'annotation': factory.xsd_annotation,
        'simpleType': xsd_simple_type.xsd_simpleType,
    })


class XsdAttribute(base.XsdBase):
    def __init__(self, attrs, parent_element, parent_schema, factory):
        super(XsdAttribute, self).__init__(attrs)

        self.schema = parent_schema
        self.prohibited = self.attr('use') == 'prohibited'

        default = self.attr('default')
        fixed = self.attr('fixed')
        assert default is None or fixed is None, \
            'Default and fixed can never be in effect at the same time'

        if isinstance(parent_element, xsd_schema.XsdSchema):
            assert self.attr('name') is not None

            qualified = parent_element.schema_element.target_ns is not None

            attribute = dumco.schema.model.Attribute(
                self.attr('name'), default if fixed is None else fixed,
                fixed is not None, qualified, parent_schema.schema_element)

            self.schema_element = dumco.schema.uses.AttributeUse(
                None, False, self.attr('use') == 'required', attribute)
        else:
            form = self.attr('form')
            if form is not None:
                qualified = (form == 'qualified')
            else:
                qualified = parent_schema.attributes_qualified

            if self.attr('ref') is not None:
                self.schema_element = dumco.schema.uses.AttributeUse(
                    default if fixed is None else fixed, fixed is not None,
                    self.attr('use') == 'required', None)
            else:
                assert self.attr('name') is not None

                attribute = dumco.schema.model.Attribute(
                    self.attr('name'), default if fixed is None else fixed,
                    fixed is not None, qualified, parent_schema.schema_element)

                self.schema_element = dumco.schema.uses.AttributeUse(
                    None, False, self.attr('use') == 'required', attribute)

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
                dumco.schema.xsd_types.st_urtype()
            for t in self.children:
                assert isinstance(t, xsd_simple_type.XsdSimpleType), \
                    'Attribute can contain only its type'

                self.schema_element.attribute.type = t.finalize(factory)

        return self.schema_element
