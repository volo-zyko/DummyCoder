# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.enums
import dumco.schema.uses

import xsd_all
import xsd_base
import xsd_choice
import xsd_sequence


def xsd_group(attrs, parent_element, factory, schema_path, all_schemata):
    new_element = XsdGroup(attrs, all_schemata[schema_path], factory)
    parent_element.children.append(new_element)

    factory.add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                                 'groups')

    return (new_element, {
        'all': xsd_all.xsd_all,
        'annotation': factory.noop_handler,
        'choice': xsd_choice.xsd_choice,
        'sequence': xsd_sequence.xsd_sequence,
    })


class XsdGroup(xsd_base.XsdBase):
    def __init__(self, attrs, parent_schema, factory):
        super(XsdGroup, self).__init__(attrs)

        self.schema = parent_schema
        self.min_occurs = factory.particle_min_occurs(attrs)
        self.max_occurs = factory.particle_max_occurs(attrs)

    @method_once
    def finalize(self, factory):
        term = None
        if self.attr('ref') is not None:
            particle = factory.resolve_group(self.attr('ref'), self.schema)

            term = particle.term
        else:
            for c in self.children:
                assert ((isinstance(c, xsd_all.XsdAll) or
                         isinstance(c, xsd_choice.XsdChoice) or
                         isinstance(c, xsd_sequence.XsdSequence)) and
                        term is None), 'Wrong content of Group'

                term = c.finalize(factory).term

        return dumco.schema.uses.Particle(
            False, self.min_occurs, self.max_occurs, term)
