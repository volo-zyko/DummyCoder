# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.model
import dumco.schema.uses
import dumco.schema.xsd_types

import base
import xsd_complex_type
import xsd_simple_type


def xsd_element(attrs, parent_element, factory, schema_path, all_schemata):
    new_element = XsdElement(attrs, all_schemata[schema_path], factory)
    parent_element.children.append(new_element)

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
    def __init__(self, attrs, parent_schema, factory):
        super(XsdElement, self).__init__(attrs)

        self.qualified = (
            self.attr('form') == 'qualified' or
            (self.attr('form') != 'unqualified' and
             parent_schema is not None and
             parent_schema.elements_qualified))
        self.abstract = (self.attr('abstract') == 'true' or
                         self.attr('abstract') == '1')

        default = self.attr('default')
        fixed = self.attr('fixed')
        assert default is None or fixed is None, \
            'Default and fixed can never be in effect at the same time'

        element = dumco.schema.model.Element(
            self.attr('name'),
            default if fixed is None else fixed,
            fixed is not None,
            parent_schema.schema_element)

        self.schema = parent_schema
        self.schema_element = dumco.schema.uses.Particle(
            self.qualified,
            factory.particle_min_occurs(attrs),
            factory.particle_max_occurs(attrs),
            element)

    @method_once
    def finalize(self, factory):
        if self.attr('substitutionGroup') is not None:
            (xsd_subst_head, _) = factory.resolve_element(
                self.attr('substitutionGroup'), self.schema, finalize=True)
            factory.add_substitution_group(xsd_subst_head, self)

        if self.attr('ref') is not None:
            (_, self.schema_element.term) = \
                factory.resolve_element(self.attr('ref'), self.schema)
        elif self.attr('type') is not None:
            self.schema_element.term.type = \
                factory.resolve_type(self.attr('type'), self.schema)
        else:
            self.schema_element.term.type = dumco.schema.xsd_types.ct_urtype()
            for t in self.children:
                assert (isinstance(t, xsd_complex_type.XsdComplexType) or
                        isinstance(t, xsd_simple_type.XsdSimpleType)), \
                    'Element can contain only its type'

                if isinstance(t, xsd_simple_type.XsdSimpleType):
                    self.schema_element.term.type = t.finalize(factory)
                else:
                    self.schema_element.term.type = t.schema_element

        if self.schema_element.max_occurs == 0:
            return None

        return self.schema_element
