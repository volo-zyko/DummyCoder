# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

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
        self.particle = None
        self.attr_uses = []

    @method_once
    def finalize(self, factory):
        for c in self.children:
            if (isinstance(c, xsd_all.XsdAll) or
                isinstance(c, xsd_choice.XsdChoice) or
                isinstance(c, xsd_sequence.XsdSequence) or
                isinstance(c, xsd_group.XsdGroup)):
                assert self.particle is None, 'Content model overriden'
                self.particle = c.finalize(factory)
            elif isinstance(c, xsd_attribute_group.XsdAttributeGroup):
                self.attr_uses.extend(c.finalize(factory).attr_uses)
            elif isinstance(c, xsd_attribute.XsdAttribute):
                if not c.prohibited:
                    self.attr_uses.append(c.finalize(factory))
            elif isinstance(c, xsd_any.XsdAny):
                self.attr_uses.append(c.finalize(factory))
            else: # pragma: no cover
                assert False, 'Wrong content of complex Extension'

        base = factory.resolve_complex_type(self.attr('base'),
                                            self.schema, finalize=True)

        self.particle = self._merge_content(base)
        self.attr_uses.extend(base.attribute_uses)

        return self

    def _merge_content(self, base):
        if self.particle is None:
            return base.particle
        elif base.particle is None:
            return self.particle

        new_element = dumco.schema.elements.Sequence(self.schema.schema_element)
        copy_base = dumco.schema.uses.Particle(None,
                                               base.particle.min_occurs,
                                               base.particle.max_occurs,
                                               base.particle.term)
        copy_self = dumco.schema.uses.Particle(None,
                                               self.particle.min_occurs,
                                               self.particle.max_occurs,
                                               self.particle.term)
        new_element.particles.extend([copy_base, copy_self])

        return dumco.schema.uses.Particle(None, 1, 1, new_element)
