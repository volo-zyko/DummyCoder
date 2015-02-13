# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.model
import dumco.schema.uses

import base


def xsd_any(attrs, parent_element, factory, schema_path, all_schemata):
    new_element = XsdAny(attrs, all_schemata[schema_path], factory, False)
    parent_element.children.append(new_element)

    return (new_element, {
        'annotation': factory.noop_handler,
    })


def xsd_anyAttribute(attrs, parent_element, factory,
                     schema_path, all_schemata):
    new_element = XsdAny(attrs, all_schemata[schema_path], factory, True)
    parent_element.children.append(new_element)

    return (new_element, {
        'annotation': factory.noop_handler,
    })


class XsdAny(base.XsdBase):
    def __init__(self, attrs, parent_schema, factory, is_attribute):
        super(XsdAny, self).__init__(attrs)

        constraints = []
        Any = dumco.schema.model.Any

        if self.attr('namespace') is not None:
            value = self.attr('namespace').strip()
            if value == '##any':
                constraints = []
            elif value == '##other':
                if parent_schema.schema_element.target_ns is not None:
                    constraints = [Any.Not(
                        Any.Name(parent_schema.schema_element.target_ns, None))]
            else:
                def fold_namespaces(accum, u):
                    if u == '##targetNamespace':
                        if parent_schema.schema_element.target_ns is None:
                            return accum
                        return accum + [Any.Name(
                            parent_schema.schema_element.target_ns, None)]
                    elif u == '##local':
                        return accum
                    return accum + [Any.Name(u, None)]

                constraints = reduce(fold_namespaces, value.split(), [])

        if len(constraints) == 0:
            anys = [Any(None, parent_schema.schema_element)]
        elif len(constraints) == 1:
            anys = [Any(constraints[0], parent_schema.schema_element)]
        else:
            anys = [Any(c, parent_schema.schema_element) for c in constraints]

        if is_attribute:
            uses = [dumco.schema.uses.AttributeUse(None, False, False, a)
                    for a in anys]
        else:
            min_occurs = factory.particle_min_occurs(attrs)
            max_occurs = factory.particle_max_occurs(attrs)

            uses = []
            if max_occurs > 0:
                uses = [dumco.schema.uses.Particle(min_occurs, max_occurs, a)
                        for a in anys]

        if len(uses) == 0:
            self.schema_element = None
        if len(uses) == 1:
            self.schema_element = uses[0]
        else:
            self.schema_element = \
                dumco.schema.uses.Particle(1, 1, dumco.schema.model.Choice())
            self.schema_element.term.members = uses

    @method_once
    def finalize(self, factory):
        return self.schema_element
