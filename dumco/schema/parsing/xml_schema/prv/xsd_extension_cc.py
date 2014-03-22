# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.checks
import dumco.schema.elements
import dumco.schema.enums
import dumco.schema.uses

import xsd_all
import xsd_any
import xsd_attribute
import xsd_attribute_group
import xsd_base
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


class XsdComplexExtension(xsd_base.XsdBase):
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

        base = factory.resolve_complex_type(self.attr('base'),
                                            self.schema, finalize=True)

        self.part = self._merge_content(base)
        self.attr_uses.extend(map(lambda (_, x): x, base.attribute_uses()))

        return self

    def _merge_content(self, base):
        base_part = _root_particle(base)

        if self.part is None:
            return base_part
        elif base_part is None:
            return self.part

        new_elem = dumco.schema.elements.Sequence(self.schema.schema_element)
        copy_base = dumco.schema.uses.Particle(False,
                                               base_part.min_occurs,
                                               base_part.max_occurs,
                                               base_part.term)
        copy_self = dumco.schema.uses.Particle(False,
                                               self.part.min_occurs,
                                               self.part.max_occurs,
                                               self.part.term)
        new_elem.members.extend([copy_base, copy_self])

        return dumco.schema.uses.Particle(False, 1, 1, new_elem)


def _root_particle(ct):
    if ct.structure is None or len(ct.structure.term.members) == 0:
        return None

    if (dumco.schema.checks.is_attribute_use(ct.structure.term.members[0]) or
            dumco.schema.checks.is_text(ct.structure.term.members[-1])):
        roots = filter(lambda x: dumco.schema.checks.is_particle(x),
                       ct.structure.term.members)
        return roots[0] if len(roots) == 1 else None

    return ct.structure
