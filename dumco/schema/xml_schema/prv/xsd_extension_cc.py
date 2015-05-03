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
import xsd_any_attribute
import xsd_attribute
import xsd_attribute_group
import xsd_choice
import xsd_group
import xsd_sequence


def xsd_extension(attrs, parent, builder, schema_path, all_schemata):
    base_name = builder.get_attribute(attrs, 'base')
    base_name = builder.parse_qname(base_name)

    new_element = XsdComplexExtension(base_name,
                                      parent_schema=all_schemata[schema_path])
    parent.children.append(new_element)

    return (new_element, {
        'all': xsd_all.xsd_all,
        'annotation': builder.noop_handler,
        'anyAttribute': xsd_any_attribute.xsd_anyAttribute,
        'attribute': xsd_attribute.xsd_attribute,
        'attributeGroup': xsd_attribute_group.xsd_attributeGroup,
        'choice': xsd_choice.xsd_choice,
        'group': xsd_group.xsd_group,
        'sequence': xsd_sequence.xsd_sequence,
    })


class XsdComplexExtension(base.XsdBase):
    def __init__(self, base_name, parent_schema=None):
        super(XsdComplexExtension, self).__init__()

        self.base_name = base_name
        self.parent_schema = parent_schema

    @method_once
    def finalize(self, builder):
        part = None
        attr_uses = []

        for c in self.children:
            if (isinstance(c, xsd_all.XsdAll) or
                    isinstance(c, xsd_choice.XsdChoice) or
                    isinstance(c, xsd_sequence.XsdSequence) or
                    isinstance(c, xsd_group.XsdGroup)):
                assert part is None, 'Content model overridden'
                part = c.finalize(builder)
            elif isinstance(c, xsd_attribute_group.XsdAttributeGroup):
                attr_uses.extend(c.finalize(builder))
            elif isinstance(c, xsd_attribute.XsdAttribute):
                if not c.prohibited:
                    attr_uses.append(c.finalize(builder))
            elif isinstance(c, xsd_any_attribute.XsdAnyAttribute):
                attr_uses.append(c.finalize(builder))
            else:  # pragma: no cover
                assert False, 'Wrong content of complex Extension'

        base_ct = builder.resolve_complex_type(self.base_name,
                                               self.parent_schema)

        part = _merge_content(part, base_ct)
        attr_uses.extend(base_ct.attribute_uses())

        return (part, attr_uses)


def _merge_content(part, base_ct):
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

    if part is None:
        return base_part
    elif base_part is None:
        return part

    new_seq = dumco.schema.model.Sequence()
    copy_self = dumco.schema.uses.Particle(part.min_occurs,
                                           part.max_occurs,
                                           part.term)
    new_seq.members.extend([base_part, copy_self])

    return dumco.schema.uses.Particle(1, 1, new_seq)
