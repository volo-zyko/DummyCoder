# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.model
import dumco.schema.uses
import dumco.schema.xsd_types

import base
import utils
import xsd_complex_type
import xsd_schema
import xsd_simple_type


def xsd_element(attrs, parent, factory, schema_path, all_schemata):
    default = factory.get_attribute(attrs, 'default', default=None)
    fixed = factory.get_attribute(attrs, 'fixed', default=None)
    assert default is None or fixed is None, \
        'Default and fixed can never be in effect at the same time'

    subst_name = factory.get_attribute(attrs, 'substitutionGroup', default=None)
    subst_name = factory.parse_qname(subst_name)

    abstract = factory.get_attribute(attrs, 'abstract', default=False)
    abstract = (abstract == 'true' or abstract == '1')

    if isinstance(parent, xsd_schema.XsdSchema):
        name = factory.get_attribute(attrs, 'name')
        type_name = factory.get_attribute(attrs, 'type', default=None)
        type_name = factory.parse_qname(type_name)

        qualified = parent.dom_element.target_ns is not None

        element = dumco.schema.model.Element(
            name, default if fixed is None else fixed, fixed is not None,
            qualified, all_schemata[schema_path].dom_element)

        particle = dumco.schema.uses.Particle(
            factory.particle_min_occurs(attrs),
            factory.particle_max_occurs(attrs),
            element)

        new_element = XsdElement(particle, type_name=type_name,
                                 subst_group_name=subst_name, abstract=abstract,
                                 parent_schema=all_schemata[schema_path])
    else:
        form = factory.get_attribute(attrs, 'form', default=None)

        if form is not None:
            qualified = (form == 'qualified')
        else:
            qualified = all_schemata[schema_path].elements_qualified

        ref = factory.get_attribute(attrs, 'ref', default=None)
        ref = factory.parse_qname(ref)
        if ref is not None:
            particle = dumco.schema.uses.Particle(
                factory.particle_min_occurs(attrs),
                factory.particle_max_occurs(attrs),
                None)
        else:
            name = factory.get_attribute(attrs, 'name')

            element = dumco.schema.model.Element(
                name, default if fixed is None else fixed, fixed is not None,
                qualified, all_schemata[schema_path].dom_element)

            particle = dumco.schema.uses.Particle(
                factory.particle_min_occurs(attrs),
                factory.particle_max_occurs(attrs),
                element)

        new_element = XsdElement(particle, ref_name=ref,
                                 subst_group_name=subst_name, abstract=abstract,
                                 parent_schema=all_schemata[schema_path])

    parent.children.append(new_element)

    factory.add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                                 'elements')

    return (new_element, {
        'annotation': factory.xsd_annotation,
        'complexType': xsd_complex_type.xsd_complexType,
        'key': factory.noop_handler,
        'keyref': factory.noop_handler,
        'simpleType': xsd_simple_type.xsd_simpleType,
        'unique': factory.noop_handler,
    })


class XsdElement(base.XsdBase):
    def __init__(self, particle, ref_name=None, type_name=None,
                 subst_group_name=None, abstract=False, parent_schema=None):
        super(XsdElement, self).__init__()

        self.dom_element = particle
        self.ref_name = ref_name
        self.type_name = type_name
        self.subst_group_name = subst_group_name
        self.abstract = abstract
        self.parent_schema = parent_schema

    @method_once
    def finalize(self, factory):
        if self.ref_name is not None:
            part = factory.resolve_element(self.ref_name, self.parent_schema)
            assert part.dom_element.term is not None

            self.dom_element.term = part.dom_element.term
        elif self.type_name is not None:
            self.dom_element.term.type = \
                factory.resolve_type(self.type_name, self.parent_schema, False)
        else:
            self.dom_element.term.type = dumco.schema.xsd_types.ct_urtype()
            for t in self.children:
                assert (isinstance(t, xsd_complex_type.XsdComplexType) or
                        isinstance(t, xsd_simple_type.XsdSimpleType)), \
                    'Element can contain only its type'

                if isinstance(t, xsd_simple_type.XsdSimpleType):
                    self.dom_element.term.type = t.finalize(factory)
                else:
                    self.dom_element.term.type = t.dom_element

        if self.subst_group_name is not None:
            substitution_head = factory.resolve_element(
                self.subst_group_name, self.parent_schema)
            substitution_head.finalize(factory)

            factory.add_substitution_group(substitution_head, self)

        if self.dom_element.max_occurs == 0:
            return None

        return self.dom_element

    def dump(self, context):
        with utils.XsdTagGuard('element', context):
            if self.ref_name is not None:
                context.add_attribute('ref',
                                      context.qname(self.dom_element.term))

                # utils.dump_value_constraint(self.dom_element.constraint,
                #                             context)

                return
