# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import xsd_any
import xsd_base
import xsd_attribute


def xsd_attributeGroup(attrs, parent_element, factory, schema_path, all_schemata):
    new_element = XsdAttributeGroup(attrs, all_schemata[schema_path])
    parent_element.children.append(new_element)

    factory.add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                                 'attribute_groups')

    return (new_element, {
        'annotation': factory.noop_handler,
        'anyAttribute': xsd_any.xsd_anyAttribute,
        'attribute': xsd_attribute.xsd_attribute,
        'attributeGroup': xsd_attributeGroup,
    })


class XsdAttributeGroup(xsd_base.XsdBase):
    def __init__(self, attrs, parent_schema):
        super(XsdAttributeGroup, self).__init__(attrs)

        self.schema = parent_schema
        self.attributes = []

    @method_once
    def finalize(self, factory):
        if self.attr('ref') is not None:
            attr_group = factory.resolve_attribute_group(self.attr('ref'),
                                                         self.schema)

            self.attributes = attr_group.attributes

            for attr in self.attributes:
                factory.fix_imports(self.schema.schema_element, attr.attribute)
        else:
            for c in self.children:
                assert (isinstance(c, XsdAttributeGroup) or
                        isinstance(c, xsd_attribute.XsdAttribute) or
                        isinstance(c, xsd_any.XsdAny)), \
                    'Attribute group contains non-attribute*'

                if isinstance(c, XsdAttributeGroup):
                    c.finalize(factory)
                    self.attributes.extend(c.attributes)
                elif isinstance(c, xsd_attribute.XsdAttribute):
                    if not c.prohibited:
                        self.attributes.append(c.finalize(factory))
                elif isinstance(c, xsd_any.XsdAny):
                    self.attributes.append(c.finalize(factory))

        return self
