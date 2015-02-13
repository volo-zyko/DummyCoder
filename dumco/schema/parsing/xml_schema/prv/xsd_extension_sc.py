# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.checks

import base
import xsd_any
import xsd_attribute
import xsd_attribute_group


def xsd_extension_in_simpleContent(attrs, parent_element, factory,
                                   schema_path, all_schemata):
    new_element = XsdSimpleExtension(attrs, all_schemata[schema_path])
    parent_element.children.append(new_element)

    return (new_element, {
        'annotation': factory.noop_handler,
        'anyAttribute': xsd_any.xsd_anyAttribute,
        'attribute': xsd_attribute.xsd_attribute,
        'attributeGroup': xsd_attribute_group.xsd_attributeGroup,
    })


class XsdSimpleExtension(base.XsdBase):
    def __init__(self, attrs, parent_schema):
        super(XsdSimpleExtension, self).__init__(attrs)

        self.schema = parent_schema
        self.base = None
        self.attr_uses = []

    @method_once
    def finalize(self, factory):
        for c in self.children:
            assert (isinstance(c, xsd_attribute_group.XsdAttributeGroup) or
                    isinstance(c, xsd_attribute.XsdAttribute) or
                    isinstance(c, xsd_any.XsdAny)), \
                'Wrong content of simple Extension'

            if isinstance(c, xsd_attribute_group.XsdAttributeGroup):
                self.attr_uses.extend(c.finalize(factory).attr_uses)
            elif isinstance(c, xsd_attribute.XsdAttribute):
                if not c.prohibited:
                    self.attr_uses.append(c.finalize(factory))
            elif isinstance(c, xsd_any.XsdAny):
                self.attr_uses.append(c.finalize(factory))

        base_type = factory.resolve_type(self.attr('base'), self.schema, True)

        if dumco.schema.checks.is_complex_type(base_type):
            self.attr_uses.extend(base_type.attribute_uses())

            self.base = base_type.text().type
            assert dumco.schema.checks.is_primitive_type(self.base), \
                'Simple Extension must extend only Simple Content'
        else:
            self.base = base_type

        return self
