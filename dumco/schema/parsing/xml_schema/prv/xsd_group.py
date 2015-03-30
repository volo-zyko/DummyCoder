# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.checks
import dumco.schema.enums
import dumco.schema.model
import dumco.schema.uses

import base
import utils
import xsd_all
import xsd_choice
import xsd_sequence


def xsd_group(attrs, parent, factory, schema_path, all_schemata):
    ref = factory.get_attribute(attrs, 'ref', default=None)
    ref = factory.parse_qname(ref)

    min_occurs = factory.particle_min_occurs(attrs)
    max_occurs = factory.particle_max_occurs(attrs)

    new_element = XsdGroup(ref, min_occurs, max_occurs,
                           parent_schema=all_schemata[schema_path])
    parent.children.append(new_element)

    factory.add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                                 'groups')

    return (new_element, {
        'all': xsd_all.xsd_all,
        'annotation': factory.noop_handler,
        'choice': xsd_choice.xsd_choice,
        'sequence': xsd_sequence.xsd_sequence,
    })


class XsdGroup(base.XsdBase):
    def __init__(self, name, min_occurs, max_occurs, parent_schema=None):
        super(XsdGroup, self).__init__()

        self.name = name
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs
        self.parent_schema = parent_schema

    @method_once
    def finalize(self, factory):
        particle = None

        if self.name is not None:
            # We need this step to pass min/max occurs values to higher levels.
            particle = dumco.schema.uses.Particle(
                self.min_occurs, self.max_occurs, dumco.schema.model.Sequence())
            particle.term.members.append(
                factory.resolve_group(self.name, self.parent_schema))
        else:
            for c in self.children:
                assert ((isinstance(c, xsd_all.XsdAll) or
                         isinstance(c, xsd_choice.XsdChoice) or
                         isinstance(c, xsd_sequence.XsdSequence)) and
                        particle is None), 'Wrong content of Group'

                particle = c.finalize(factory)

        return utils.reduce_particle(particle)

    def dump(self, context):
        with utils.XsdTagGuard('group', context):
            if self.children:
                context.add_attribute('name', self.name)

                for c in self.children:
                    c.dump(context)
            else:
                context.add_attribute('ref', self.name)
