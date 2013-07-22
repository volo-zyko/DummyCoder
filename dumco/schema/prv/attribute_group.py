# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.base
import dumco.schema.checks

from resolvers import resolve_attribute_group


class AttributeGroup(dumco.schema.base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(AttributeGroup, self).__init__(attrs, parent_schema)

        self.attributes = []

    @method_once
    def finalize(self, factory):
        if self.attr('ref') is not None:
            a = resolve_attribute_group(self.attr('ref'), self.schema)
            a.finalize(factory)

            self.attributes = a.attributes
        else:
            for c in self.children:
                assert (isinstance(c, AttributeGroup) or
                        dumco.schema.checks.is_attribute(c.attribute) or
                        dumco.schema.checks.is_any(c.attribute)), \
                    'Attribute group contains non-attribute*'

                if isinstance(c, AttributeGroup):
                    c.finalize(factory)
                    self.attributes.extend(c.attributes)
                elif (dumco.schema.checks.is_attribute(c.attribute) or
                      dumco.schema.checks.is_any(c.attribute)):
                    c.attribute = c.attribute.finalize(factory)
                    self.attributes.append(c)

        return super(AttributeGroup, self).finalize(None)
