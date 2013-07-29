# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.checks
import dumco.schema.elements
import dumco.schema.namer

import xsd_any
import xsd_attribute
import xsd_attribute_group
import xsd_base
import xsd_complex_type
import xsd_element
import xsd_group
import xsd_sequence
import xsd_simple_type


def xsd_schema(attrs, parent_element, factory, schema_path, all_schemata):
    schema = XsdSchema(attrs, schema_path)
    all_schemata[schema_path] = schema

    for (prefix, uri) in factory.namespaces.iteritems():
        schema.schema_element.set_namespace(prefix, uri)

    return (schema, {
        'annotation': factory.noop_handler,
        'attribute': xsd_attribute.xsd_attribute,
        'attributeGroup': xsd_attribute_group.xsd_attributeGroup,
        'complexType': xsd_complex_type.xsd_complexType,
        'element': xsd_element.xsd_element,
        'group': xsd_group.xsd_group,
        'import': factory.xsd_import,
        'notation': factory.noop_handler,
        'simpleType': xsd_simple_type.xsd_simpleType,
    })


class XsdSchema(xsd_base.XsdBase):
    def __init__(self, attrs, schema_path):
        super(XsdSchema, self).__init__(attrs)

        self.attributes_qualified = \
            self.attr('attributeFormDefault') == 'qualified'
        self.elements_qualified = \
            self.attr('elementFormDefault') == 'qualified'

        self.schema_element = dumco.schema.elements.Schema(
            self.attr('targetNamespace'), schema_path)

        self.attributes = {}
        self.attribute_groups = {}
        self.complex_types = {}
        self.elements = {}
        self.groups = {}
        self.imports = {}
        self.namespaces = {}
        self.simple_types = {}
        self.unnamed_types = []

    def set_imports(self, all_schemata):
        self.schema_element.set_imports(self.imports.iterkeys(),
            {path: all_schemata[path].schema_element
             for path in self.imports.iterkeys()})

        self.imports = {
            all_schemata[path].schema_element.target_ns: all_schemata[path]
            for path in self.imports.iterkeys()}

    @method_once
    def finalize(self, all_schemata, factory):
        forged_names = dumco.schema.namer.ValidatingNameSet()

        for name in sorted(self.simple_types.iterkeys()):
            schema_st = self.simple_types[name].finalize(factory)
            schema_st.nameit([self], factory.namer, forged_names)
            self.schema_element.simple_types[schema_st.name] = schema_st

        for name in sorted(self.complex_types.iterkeys()):
            schema_ct = self.complex_types[name].finalize(factory)
            schema_ct.nameit([self], factory.namer, forged_names)
            self.schema_element.complex_types[schema_ct.name] = schema_ct

        for (parents, t) in sorted(self.unnamed_types,
                                   key=lambda x: len(x[0])):
            schema_type = t.finalize(factory)
            schema_type.nameit(parents, factory.namer, forged_names)

            if dumco.schema.checks.is_complex_type(schema_type):
                self.schema_element.complex_types[schema_type.name] = \
                    schema_type
            elif dumco.schema.checks.is_simple_type(schema_type):
                self.schema_element.simple_types[schema_type.name] = \
                    schema_type

        for elem in self.elements.itervalues():
            schema_elem = elem.finalize(factory)
            self.schema_element.elements[schema_elem.term.name] = schema_elem

        for attr in self.attributes.itervalues():
            schema_attr = attr.finalize(factory)
            name = schema_attr.attribute.name
            self.schema_element.attributes[name] = schema_attr
