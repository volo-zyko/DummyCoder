# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.base
import dumco.schema.checks

import attribute_group
import complex_content
import group
from resolvers import resolve_complex_type


class ComplexRestriction(dumco.schema.base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(ComplexRestriction, self).__init__(attrs, parent_schema)

        self.term = None
        self.attributes = []

    @method_once
    def finalize(self, factory):
        for c in self.children:
            if (dumco.schema.checks.is_particle(c) and
                (dumco.schema.checks.is_compositor(c.element) or
                 isinstance(c.element, group.Group))):
                assert self.term is None, 'Content model overriden'
                c.element = c.element.finalize(factory)
                self.term = c
            elif isinstance(c, attribute_group.AttributeGroup):
                c.finalize(factory)
                self.attributes.extend(c.attributes)
            elif (dumco.schema.checks.is_attribute_use(c) and
                  (dumco.schema.checks.is_attribute(c.attribute) or
                   dumco.schema.checks.is_any(c.attribute))):
                c.attribute = c.attribute.finalize(factory)
                self.attributes.append(c)
            else:
                assert False, 'Wrong content of complex Restriction'

        return super(ComplexRestriction, self).finalize(None)
