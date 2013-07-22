# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.base
import dumco.schema.checks

import attribute_group
from resolvers import resolve_type


class SimpleExtension(dumco.schema.base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(SimpleExtension, self).__init__(attrs, parent_schema)

        self.base = None
        self.attributes = []

    @method_once
    def finalize(self, factory):
        self.base = resolve_type(self.attr('base'), self.schema, factory)
        self.base.finalize(factory)

        for c in self.children:
            assert (dumco.schema.checks.is_simple_type(c) or
                    isinstance(c, attribute_group.AttributeGroup) or
                    dumco.schema.checks.is_attribute(c.attribute) or
                    dumco.schema.checks.is_any(c.attribute)), \
                'Wrong content of simple Extension'

            if dumco.schema.checks.is_simple_type(c):
                continue
            elif isinstance(c, attribute_group.AttributeGroup):
                c.finalize(factory)
                self.attributes.extend(c.attributes)
            elif (dumco.schema.checks.is_attribute(c.attribute) or
                  dumco.schema.checks.is_any(c.attribute)):
                c.attribute = c.attribute.finalize(factory)
                self.attributes.append(c)

        return super(SimpleExtension, self).finalize(None)
