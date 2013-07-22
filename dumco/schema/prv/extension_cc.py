# Distributed under the GPLv2 License; see accompanying file COPYING.

import copy

from dumco.utils.decorators import method_once

import dumco.schema.base
import dumco.schema.checks
import dumco.schema.sequence
import dumco.schema.uses

import attribute_group
import complex_content
import group
from resolvers import resolve_complex_type


class ComplexExtension(dumco.schema.base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(ComplexExtension, self).__init__(attrs, parent_schema)

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
                assert False, 'Wrong content of complex Extension'

        base = resolve_complex_type(self.attr('base'), self.schema)
        base.finalize(factory)

        self.term = self._merge_content(base, factory)
        self.attributes.extend(base.attributes)

        return super(ComplexExtension, self).finalize(None)

    def _merge_content(self, base, factory):
        if self.term is None:
            return base.term
        elif base.term is None:
            return self.term

        new_element = dumco.schema.sequence.Sequence({}, self.schema)
        copy_base = copy.copy(base.term)
        copy_self = copy.copy(self.term)
        copy_base.name = None
        copy_self.name = None
        new_element.children.extend([copy_base, copy_self])
        new_element.finalize(factory)

        return dumco.schema.uses.Particle({}, new_element, factory)
