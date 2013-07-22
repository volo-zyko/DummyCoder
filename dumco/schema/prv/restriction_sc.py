# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.checks
import dumco.schema.restriction

import attribute_group
from resolvers import resolve_type


class SimpleRestriction(dumco.schema.restriction.Restriction):
    def __init__(self, attrs, parent_schema):
        super(SimpleRestriction, self).__init__(attrs, parent_schema)

        self.attributes = []

    @method_once
    def finalize(self, factory):
        for c in self.children:
            assert (dumco.schema.checks.is_simple_type(c) or
                    isinstance(c, attribute_group.AttributeGroup) or
                    dumco.schema.checks.is_attribute(c.attribute) or
                    dumco.schema.checks.is_any(c.attribute)), \
                'Wrong content of simple Restriction'

            if dumco.schema.checks.is_simple_type(c):
                self.base = c
            elif isinstance(c, attribute_group.AttributeGroup):
                c.finalize(factory)
                self.attributes.extend(c.attributes)
            elif (dumco.schema.checks.is_attribute(c.attribute) or
                  dumco.schema.checks.is_any(c.attribute)):
                c.attribute = c.attribute.finalize(factory)
                self.attributes.append(c)

        if self.base is None and self.attr('base') is not None:
            base = resolve_type(self.attr('base'), self.schema, factory)
            base.finalize(factory)

            assert ((dumco.schema.checks.is_complex_type(base) and
                     dumco.schema.checks.has_simple_content(base)) or
                    dumco.schema.checks.is_primitive_type(base)), \
                'Wrong base type of simple Restriction'

            if (dumco.schema.checks.is_complex_type(base) and
                dumco.schema.checks.has_simple_content(base)):
                self.base = base.text.type

        return super(SimpleRestriction, self).finalize(None)
