# Distributed under the GPLv2 License; see accompanying file COPYING.

import copy

from dumco.utils.decorators import method_once

import dumco.schema.checks
import dumco.schema.model
import dumco.schema.enums
import dumco.schema.uses

import base
import utils
import xsd_all
import xsd_any
import xsd_attribute
import xsd_attribute_group
import xsd_choice
import xsd_group
import xsd_sequence


def xsd_extension_in_complexContent(attrs, parent_element, factory,
                                    schema_path, all_schemata):
    new_element = XsdComplexExtension(attrs, all_schemata[schema_path])
    parent_element.children.append(new_element)

    return (new_element, {
        'all': xsd_all.xsd_all,
        'annotation': factory.noop_handler,
        'anyAttribute': xsd_any.xsd_anyAttribute,
        'attribute': xsd_attribute.xsd_attribute,
        'attributeGroup': xsd_attribute_group.xsd_attributeGroup,
        'choice': xsd_choice.xsd_choice,
        'group': xsd_group.xsd_group,
        'sequence': xsd_sequence.xsd_sequence,
    })


class XsdComplexExtension(base.XsdBase):
    def __init__(self, attrs, parent_schema):
        super(XsdComplexExtension, self).__init__(attrs)

        self.schema = parent_schema
        self.part = None
        self.attr_uses = []

    @method_once
    def finalize(self, factory):
        for c in self.children:
            if (isinstance(c, xsd_all.XsdAll) or
                    isinstance(c, xsd_choice.XsdChoice) or
                    isinstance(c, xsd_sequence.XsdSequence) or
                    isinstance(c, xsd_group.XsdGroup)):
                assert self.part is None, 'Content model overridden'
                self.part = c.finalize(factory)
            elif isinstance(c, xsd_attribute_group.XsdAttributeGroup):
                self.attr_uses.extend(c.finalize(factory).attr_uses)
            elif isinstance(c, xsd_attribute.XsdAttribute):
                if not c.prohibited:
                    self.attr_uses.append(c.finalize(factory))
            elif isinstance(c, xsd_any.XsdAny):
                self.attr_uses.append(c.finalize(factory))
            else:  # pragma: no cover
                assert False, 'Wrong content of complex Extension'

        base_ct = factory.resolve_complex_type(self.attr('base'),
                                               self.schema, finalize=True)

        self.part = self._merge_content(base_ct)
        self.attr_uses.extend(base_ct.attribute_uses())

        return self

    def _merge_content(self, base_ct):
        assert base_ct is not None

        base_part = None
        if base_ct.structure is not None:
            base_part = copy.copy(base_ct.structure)
            base_part.term = copy.copy(base_ct.structure.term)
            base_part.term.members = [m for m in base_ct.structure.term.members
                                      if dumco.schema.checks.is_particle(m)]

            if not base_part.term.members:
                base_part = None

            base_part = utils.reduce_particle(base_part)

        if self.part is None:
            return base_part
        elif base_part is None:
            return self.part

        new_seq = dumco.schema.model.Sequence()
        copy_self = dumco.schema.uses.Particle(self.part.qualified,
                                               self.part.min_occurs,
                                               self.part.max_occurs,
                                               self.part.term)
        new_seq.members.extend([base_part, copy_self])

        return dumco.schema.uses.Particle(False, 1, 1, new_seq)
