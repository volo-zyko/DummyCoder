# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.model
import dumco.schema.uses

import base
import utils


def xsd_any(attrs, parent, builder, schema_path, all_schemata):
    namespace = builder.get_attribute(attrs, 'namespace', default='##any')
    min_occurs = builder.particle_min_occurs(attrs)
    max_occurs = builder.particle_max_occurs(attrs)

    new_element = XsdAny(namespace, min_occurs, max_occurs,
                         parent_schema=all_schemata[schema_path])
    parent.children.append(new_element)

    return (new_element, {
        'annotation': builder.noop_handler,
    })


class XsdAny(base.XsdBase):
    def __init__(self, namespace, min_occurs, max_occurs, parent_schema=None):
        super(XsdAny, self).__init__()

        self.namespace = namespace
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs
        self.parent_schema = parent_schema

    @method_once
    def finalize(self, builder):
        anys = utils.parse_any_namespace(self.namespace, self.parent_schema)

        assert len(anys) != 0

        if len(anys) == 1:
            dom_any = dumco.schema.uses.Particle(self.min_occurs,
                                                 self.max_occurs, anys[0])
        else:
            dom_any = \
                dumco.schema.uses.Particle(self.min_occurs, self.max_occurs,
                                           dumco.schema.model.Choice())
            dom_any.term.members.extend([dumco.schema.model.Particle(1, 1, a)
                                         for a in anys])

        return dom_any

    def dump(self, context):
        with utils.XsdTagGuard('any', context):
            if self.min_occurs != 1:
                context.add_attribute('minOccurs', self.min_occurs)
            if self.max_occurs != 1:
                context.add_attribute('maxOccurs', self.max_occurs)

            context.add_attribute('namespace', self.namespace)
