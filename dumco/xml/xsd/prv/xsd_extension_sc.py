# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import xsd_any
import xsd_attribute
import xsd_attribute_group
import xsd_base
import xsd_simple_type


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


class XsdSimpleExtension(xsd_base.XsdBase):
    def __init__(self, attrs, parent_schema):
        super(XsdSimpleExtension, self).__init__(attrs)

        self.schema = parent_schema
        self.base = None
        self.attributes = []

    @method_once
    def finalize(self, factory):
        self.base = factory.resolve_type(self.attr('base'),
                                         self.schema, finalize=True)

        for c in self.children:
            assert (isinstance(c, xsd_attribute_group.XsdAttributeGroup) or
                    isinstance(c, xsd_attribute.XsdAttribute) or
                    isinstance(c, xsd_any.XsdAny)), \
                'Wrong content of simple Extension'

            if isinstance(c, xsd_attribute_group.XsdAttributeGroup):
                c.finalize(factory)
                self.attributes.extend(c.attributes)
            elif (isinstance(c, xsd_attribute.XsdAttribute) or
                  isinstance(c, xsd_any.XsdAny)):
                self.attributes.append(c.finalize(factory))

        return self
