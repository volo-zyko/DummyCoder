# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.elements
import dumco.schema.uses

import xsd_any
import xsd_base
import xsd_element
import xsd_group
import xsd_sequence


def xsd_choice(attrs, parent_element, factory, schema_path, all_schemata):
    new_element = XsdChoice(attrs, all_schemata[schema_path], factory)
    parent_element.children.append(new_element)

    return (new_element, {
        'annotation': factory.noop_handler,
        'any': xsd_any.xsd_any,
        'choice': xsd_choice,
        'element': xsd_element.xsd_element,
        'group': xsd_group.xsd_group,
        'sequence': xsd_sequence.xsd_sequence,
    })


class XsdChoice(xsd_base.XsdBase):
    def __init__(self, attrs, parent_schema, factory):
        super(XsdChoice, self).__init__(attrs)

        self.schema_element = dumco.schema.uses.Particle(
            factory.particle_min_occurs(attrs),
            factory.particle_max_occurs(attrs),
            dumco.schema.elements.Choice(parent_schema.schema_element))

    @method_once
    def finalize(self, factory):
        for c in self.children:
            assert (isinstance(c, xsd_any.XsdAny) or
                    isinstance(c, XsdChoice) or
                    isinstance(c, xsd_element.XsdElement) or
                    isinstance(c, xsd_group.XsdGroup) or
                    isinstance(c, xsd_sequence.XsdSequence)), \
                'Wrong content of Choice'

            self.schema_element.term.particles.append(c.finalize(factory))

        return self.schema_element
