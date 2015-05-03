# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.model
import dumco.schema.uses

import base
import utils
import xsd_element


def xsd_all(attrs, parent, builder, schema_path, all_schemata):
    min_occurs = builder.particle_min_occurs(attrs)
    max_occurs = builder.particle_max_occurs(attrs)

    particle = dumco.schema.uses.Particle(
        min_occurs, max_occurs, dumco.schema.model.Interleave())

    new_element = XsdAll(particle)
    parent.children.append(new_element)

    return (new_element, {
        'annotation': builder.noop_handler,
        'element': xsd_element.xsd_element,
    })


class XsdAll(base.XsdBase):
    def __init__(self, particle):
        super(XsdAll, self).__init__()

        self.dom_element = particle

    @method_once
    def finalize(self, builder):
        for c in self.children:
            assert isinstance(c, xsd_element.XsdElement), \
                'Only Element is allowed in All'

            self.dom_element.term.members.append(c.finalize(builder))

        return utils.reduce_particle(self.dom_element)

    def dump(self, context):
        with utils.XsdTagGuard('all', context):
            if self.dom_element.min_occurs != 1:
                context.add_attribute('minOccurs', self.dom_element.min_occurs)
            if self.dom_element.max_occurs != 1:
                context.add_attribute('maxOccurs', self.dom_element.max_occurs)

            for c in self.children:
                c.dump(context)
