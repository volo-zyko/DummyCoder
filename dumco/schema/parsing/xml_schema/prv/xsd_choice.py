# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.model
import dumco.schema.uses

import base
import utils
import xsd_any
import xsd_element
import xsd_group
import xsd_sequence


def xsd_choice(attrs, parent, factory, schema_path, all_schemata):
    min_occurs = factory.particle_min_occurs(attrs)
    max_occurs = factory.particle_max_occurs(attrs)

    particle = dumco.schema.uses.Particle(
        min_occurs, max_occurs, dumco.schema.model.Choice())

    new_element = XsdChoice(particle)
    parent.children.append(new_element)

    return (new_element, {
        'annotation': factory.noop_handler,
        'any': xsd_any.xsd_any,
        'choice': xsd_choice,
        'element': xsd_element.xsd_element,
        'group': xsd_group.xsd_group,
        'sequence': xsd_sequence.xsd_sequence,
    })


class XsdChoice(base.XsdBase):
    def __init__(self, particle, min_occurs=None, max_occurs=None):
        super(XsdChoice, self).__init__()

        self.dom_element = particle
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs

    @method_once
    def finalize(self, factory):
        for c in self.children:
            assert (isinstance(c, xsd_any.XsdAny) or
                    isinstance(c, XsdChoice) or
                    isinstance(c, xsd_element.XsdElement) or
                    isinstance(c, xsd_group.XsdGroup) or
                    isinstance(c, xsd_sequence.XsdSequence)), \
                'Wrong content of Choice'

            self.dom_element.term.members.append(c.finalize(factory))

        return utils.reduce_particle(self.dom_element)

    def dump(self, context):
        with utils.XsdTagGuard('choice', context):
            if self.dom_element.min_occurs != 1:
                context.add_attribute('minOccurs', self.dom_element.min_occurs)
            if self.dom_element.max_occurs != 1:
                context.add_attribute('maxOccurs', self.dom_element.max_occurs)

            for c in self.children:
                c.dump(context)
