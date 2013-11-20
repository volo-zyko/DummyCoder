# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.elements
import dumco.schema.uses

import xsd_base
import xsd_element


def xsd_all(attrs, parent_element, factory, schema_path, all_schemata):
    new_element = XsdAll(attrs, all_schemata[schema_path], factory)
    parent_element.children.append(new_element)

    return (new_element, {
        'annotation': factory.noop_handler,
        'element': xsd_element.xsd_element,
    })


class XsdAll(xsd_base.XsdBase):
    def __init__(self, attrs, parent_schema, factory):
        super(XsdAll, self).__init__(attrs)

        self.schema_element = dumco.schema.uses.Particle(None, None,
            factory.particle_min_occurs(attrs),
            factory.particle_max_occurs(attrs),
            dumco.schema.elements.All(parent_schema.schema_element))

    @method_once
    def finalize(self, factory):
        for c in self.children:
            assert isinstance(c, xsd_element.XsdElement), \
                'Only Element is allowed in All'

            self.schema_element.term.particles.append(c.finalize(factory))

        return self.schema_element
