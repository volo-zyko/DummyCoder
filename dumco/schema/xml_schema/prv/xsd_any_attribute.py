# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.model
import dumco.schema.uses

import base
import utils


def xsd_anyAttribute(attrs, parent, builder, schema_path, all_schemata):
    namespace = builder.get_attribute(attrs, 'namespace', default='##any')

    new_element = XsdAnyAttribute(namespace,
                                  parent_schema=all_schemata[schema_path])
    parent.children.append(new_element)

    return (new_element, {
        'annotation': builder.noop_handler,
    })


class XsdAnyAttribute(base.XsdBase):
    def __init__(self, namespace, parent_schema=None):
        super(XsdAnyAttribute, self).__init__()

        self.namespace = namespace
        self.parent_schema = parent_schema

    @method_once
    def finalize(self, builder):
        anys = utils.parse_any_namespace(self.namespace, self.parent_schema)

        assert len(anys) != 0

        if len(anys) == 1:
            dom_any = \
                dumco.schema.uses.AttributeUse(None, False, False, anys[0])
        else:
            dom_any = \
                dumco.schema.uses.Particle(1, 1, dumco.schema.model.Choice())
            dom_any.term.members.extend([
                dumco.schema.uses.AttributeUse(None, False, False, a)
                for a in anys])

        return dom_any

    def dump(self, context):
        with utils.XsdTagGuard('anyAttribute', context):
            context.add_attribute('namespace', self.namespace)
