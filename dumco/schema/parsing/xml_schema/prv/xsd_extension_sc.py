# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.checks

import base
import utils
import xsd_any_attribute
import xsd_attribute
import xsd_attribute_group


def xsd_extension(attrs, parent, factory, schema_path, all_schemata):
    base_name = factory.get_attribute(attrs, 'base')
    base_name = factory.parse_qname(base_name)

    new_element = XsdSimpleExtension(base_name,
                                     parent_schema=all_schemata[schema_path])
    parent.children.append(new_element)

    return (new_element, {
        'annotation': factory.noop_handler,
        'anyAttribute': xsd_any_attribute.xsd_anyAttribute,
        'attribute': xsd_attribute.xsd_attribute,
        'attributeGroup': xsd_attribute_group.xsd_attributeGroup,
    })


class XsdSimpleExtension(base.XsdBase):
    def __init__(self, base_name, parent_schema=None):
        super(XsdSimpleExtension, self).__init__()

        self.base_name = base_name
        self.parent_schema = parent_schema

    @method_once
    def finalize(self, factory):
        attr_uses = []

        for c in self.children:
            assert (isinstance(c, xsd_attribute_group.XsdAttributeGroup) or
                    isinstance(c, xsd_attribute.XsdAttribute) or
                    isinstance(c, xsd_any_attribute.XsdAnyAttribute)), \
                'Wrong content of simple Extension'

            if isinstance(c, xsd_attribute_group.XsdAttributeGroup):
                attr_uses.extend(c.finalize(factory))
            elif isinstance(c, xsd_attribute.XsdAttribute):
                if not c.prohibited:
                    attr_uses.append(c.finalize(factory))
            elif isinstance(c, xsd_any_attribute.XsdAnyAttribute):
                attr_uses.append(c.finalize(factory))

        base_type = factory.resolve_type(self.base_name,
                                         self.parent_schema, True)

        if dumco.schema.checks.is_complex_type(base_type):
            attr_uses.extend(base_type.attribute_uses())

            base_type = base_type.text().type
        else:
            base_type = base_type

        assert dumco.schema.checks.is_primitive_type(base_type), \
            'Simple Extension must extend only Simple Content'

        return (base_type, attr_uses)

    def dump(self, context):
        with utils.XsdTagGuard('extension', context):
            context.add_attribute('base', self.base_name)

            for c in self.children:
                c.dump(context)
