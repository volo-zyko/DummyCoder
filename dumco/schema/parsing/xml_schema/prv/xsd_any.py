# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.elements
import dumco.schema.uses

import xsd_base


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


class XsdAny(xsd_base.XsdBase):
    def __init__(self, attrs, parent_schema, factory, is_attribute):
        super(XsdAny, self).__init__(attrs)

        constraints = []
        Any = dumco.schema.elements.Any

        if self.attr('namespace') is not None:
            value = self.attr('namespace').strip()
            if value == '##any':
                constraints = []
            elif value == '##other':
                if parent_schema.schema_element.target_ns is not None:
                    constraints = Any.Not(
                        Any.Name(parent_schema.schema_element.target_ns, None))
            else:
                def fold_namespaces(accum, u):
                    if u == '##targetNamespace':
                        if parent_schema.schema_element.target_ns is None:
                            return accum
                        return accum + Any.Name(
                            parent_schema.schema_element.target_ns, None)
                    elif u == '##local':
                        return accum
                    return accum + [Any.Name(u, None)]

                constraints = reduce(fold_namespaces, value.split(), [])

        if is_attribute:
            self.schema_element = dumco.schema.uses.AttributeUse(
                False, None, False,
                Any(constraints, parent_schema.schema_element))
        else:
            self.schema_element = dumco.schema.uses.Particle(
                False,
                factory.particle_min_occurs(attrs),
                factory.particle_max_occurs(attrs),
                Any(constraints, parent_schema.schema_element))

    @method_once
    def finalize(self, factory):
        return self.schema_element
