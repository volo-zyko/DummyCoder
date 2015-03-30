# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.checks
import dumco.schema.model
import dumco.schema.uses
import dumco.schema.xsd_types

import base
import utils
import xsd_schema
import xsd_simple_type


def xsd_attribute(attrs, parent, factory, schema_path, all_schemata):
    default = factory.get_attribute(attrs, 'default', default=None)
    fixed = factory.get_attribute(attrs, 'fixed', default=None)
    assert default is None or fixed is None, \
        'Default and fixed can never be in effect at the same time'

    if isinstance(parent, xsd_schema.XsdSchema):
        name = factory.get_attribute(attrs, 'name')
        type_name = factory.get_attribute(attrs, 'type', default=None)
        type_name = factory.parse_qname(type_name)

        qualified = parent.dom_element.target_ns is not None

        attribute = dumco.schema.model.Attribute(
            name, default if fixed is None else fixed, fixed is not None,
            qualified, all_schemata[schema_path].dom_element)

        attr_use = dumco.schema.uses.AttributeUse(None, False, False, attribute)

        new_element = XsdAttribute(attr_use, type_name=type_name,
                                   parent_schema=all_schemata[schema_path])
    else:
        form = factory.get_attribute(attrs, 'form', default=None)
        use = factory.get_attribute(attrs, 'use', default=None)

        if form is not None:
            qualified = (form == 'qualified')
        else:
            qualified = all_schemata[schema_path].attributes_qualified

        ref = factory.get_attribute(attrs, 'ref', default=None)
        ref = factory.parse_qname(ref)
        if ref is not None:
            attr_use = dumco.schema.uses.AttributeUse(
                default if fixed is None else fixed, fixed is not None,
                use == 'required', None)
        else:
            name = factory.get_attribute(attrs, 'name')

            attribute = dumco.schema.model.Attribute(
                name, default if fixed is None else fixed, fixed is not None,
                qualified, all_schemata[schema_path].dom_element)

            attr_use = dumco.schema.uses.AttributeUse(
                None, False, use == 'required', attribute)

        new_element = XsdAttribute(attr_use, ref_name=ref,
                                   prohibited=(use == 'prohibited'),
                                   parent_schema=all_schemata[schema_path])

    parent.children.append(new_element)

    factory.add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                                 'attributes')

    return (new_element, {
        'annotation': factory.xsd_annotation,
        'simpleType': xsd_simple_type.xsd_simpleType,
    })


class XsdAttribute(base.XsdBase):
    def __init__(self, attr_use, ref_name=None, type_name=None,
                 prohibited=False, parent_schema=None):
        super(XsdAttribute, self).__init__()

        self.dom_element = attr_use
        self.ref_name = ref_name
        self.type_name = type_name
        self.prohibited = prohibited
        self.parent_schema = parent_schema

    @method_once
    def finalize(self, factory):
        if self.ref_name is not None:
            self.dom_element.attribute = \
                factory.resolve_attribute(self.ref_name, self.parent_schema)
        elif self.type_name is not None:
            self.dom_element.attribute.type = \
                factory.resolve_simple_type(self.type_name, self.parent_schema)
        else:
            self.dom_element.attribute.type = \
                dumco.schema.xsd_types.st_urtype()
            for t in self.children:
                assert isinstance(t, xsd_simple_type.XsdSimpleType), \
                    'Attribute can contain only its type'

                self.dom_element.attribute.type = t.finalize(factory)

        return self.dom_element

    def dump(self, context):
        with utils.XsdTagGuard('attribute', context):
            if self.ref_name is not None:
                context.add_attribute('ref',
                                      context.qname(self.dom_element.attribute))

                utils.dump_value_constraint(self.dom_element.constraint,
                                            context)

                # TODO: Move this up.
                if self.dom_element.required:
                    context.add_attribute('use', 'required')

                return

            context.add_attribute('name', self.dom_element.attribute.name)

            if not dumco.schema.checks.is_simple_urtype(
                    self.dom_element.attribute.type):
                context.add_attribute(
                    'type', context.qname(self.dom_element.attribute.type))

            if self.dom_element.constraint.value is not None:
                utils.dump_value_constraint(
                    self.dom_element.constraint, context)
            else:
                utils.dump_value_constraint(
                    self.dom_element.attribute.constraint, context)

            form = context.attribute_form(self.dom_element.attribute)
            if form is not None:
                context.add_attribute('form', form)

            # TODO: Merge this up.
            if self.dom_element.required:
                context.add_attribute('use', 'required')
