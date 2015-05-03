# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import utils
import xsd_any_attribute
import xsd_attribute


def xsd_attributeGroup(attrs, parent, builder, schema_path, all_schemata):
    ref = builder.get_attribute(attrs, 'ref', default=None)
    ref = builder.parse_qname(ref)

    new_element = XsdAttributeGroup(ref,
                                    parent_schema=all_schemata[schema_path])
    parent.children.append(new_element)

    builder.add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                                 'attribute_groups')

    return (new_element, {
        'annotation': builder.noop_handler,
        'anyAttribute': xsd_any_attribute.xsd_anyAttribute,
        'attribute': xsd_attribute.xsd_attribute,
        'attributeGroup': xsd_attributeGroup,
    })


class XsdAttributeGroup(base.XsdBase):
    def __init__(self, name, parent_schema=None):
        super(XsdAttributeGroup, self).__init__()

        self.name = name
        self.parent_schema = parent_schema

    @method_once
    def finalize(self, builder):
        attr_uses = []

        if self.name is not None:
            attr_uses = builder.resolve_attribute_group(self.name,
                                                        self.parent_schema)
        else:
            for c in self.children:
                assert (isinstance(c, XsdAttributeGroup) or
                        isinstance(c, xsd_attribute.XsdAttribute) or
                        isinstance(c, xsd_any_attribute.XsdAnyAttribute)), \
                    'Attribute group contains non-attribute*'

                if isinstance(c, XsdAttributeGroup):
                    attr_uses.extend(c.finalize(builder))
                elif isinstance(c, xsd_attribute.XsdAttribute):
                    if not c.prohibited:
                        attr_uses.append(c.finalize(builder))
                elif isinstance(c, xsd_any_attribute.XsdAnyAttribute):
                    attr_uses.append(c.finalize(builder))

        return attr_uses

    def dump(self, context):
        with utils.XsdTagGuard('attributeGroup', context):
            if self.children:
                context.add_attribute('name', self.name)

                for c in self.children:
                    c.dump(context)
            else:
                context.add_attribute('ref', self.name)
