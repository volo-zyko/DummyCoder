# Distributed under the GPLv2 License; see accompanying file COPYING.

import os.path
import StringIO

from dumco.utils.decorators import method_once

import dumco.schema.checks
import dumco.schema.model
import dumco.schema.enums
import dumco.schema.xsd_types

import dumco.schema.parsing.xml_parser

import base
import utils
import xsd_attribute
import xsd_attribute_group
import xsd_complex_type
import xsd_element
import xsd_group
import xsd_simple_type


def xsd_schema(attrs, parent_element, builder, schema_path, all_schemata):
    if dumco.schema.checks.is_xml_namespace(attrs.get('targetNamespace', None)):
        del all_schemata[schema_path]
        builder.reset()

        raise dumco.schema.parsing.xml_parser.SkipParse()

    target_ns = builder.get_attribute(attrs, 'targetNamespace', default=None)
    aqualified = builder.get_attribute(attrs, 'attributeFormDefault',
                                       default=False) == 'qualified'
    equalified = builder.get_attribute(attrs, 'elementFormDefault',
                                       default=False) == 'qualified'

    schema = dumco.schema.model.Schema(target_ns)

    assert schema_path.endswith('.xsd')
    schema.filename = os.path.splitext(os.path.basename(schema_path))[0]

    new_element = XsdSchema(schema, aqualified, equalified, path=schema_path)
    all_schemata[schema_path] = new_element

    return (new_element, {
        'annotation': builder.noop_handler,
        'attribute': xsd_attribute.xsd_attribute,
        'attributeGroup': xsd_attribute_group.xsd_attributeGroup,
        'complexType': xsd_complex_type.xsd_complexType,
        'element': xsd_element.xsd_element,
        'group': xsd_group.xsd_group,
        'import': XsdSchema.xsd_import,
        'include': XsdSchema.xsd_include,
        'notation': builder.noop_handler,
        'redefine': builder.noop_handler,
        'simpleType': xsd_simple_type.xsd_simpleType,
    })


class XsdSchema(base.XsdBase):
    def __init__(self, schema, aqualified, equalified, path=None):
        super(XsdSchema, self).__init__()

        self.dom_element = schema
        self.attributes_qualified = aqualified
        self.elements_qualified = equalified
        self.path = path

        self.attributes = {}
        self.attribute_groups = {}
        self.complex_types = {}
        self.elements = {}
        self.groups = {}
        self.imports = {}
        self.simple_types = {}
        self.unnamed_types = []

    def set_imports(self, all_schemata, builder):
        for path in all_schemata.iterkeys():
            if any([(path in included_paths) for included_paths in
                    builder.included_schema_paths.itervalues()]):
                continue

            schema = all_schemata[path]

            assert schema.dom_element.target_ns not in self.imports, \
                'Attempting to redefine imported schema for {}'.format(
                    schema.dom_element.target_ns)

            self.imports[schema.dom_element.target_ns] = schema

    @method_once
    def finalize(self, all_schemata, builder):
        for st in sorted(self.simple_types.itervalues(), key=lambda x: x.name):
            st.finalize(builder)

        for ct in sorted(self.complex_types.itervalues(), key=lambda x: x.name):
            ct.finalize(builder)

        for xsd_type in self.unnamed_types:
            xsd_type.finalize(builder)

        for elem in self.elements.itervalues():
            particle = elem.finalize(builder)
            self.dom_element.elements.append(particle.term)

        for attr in self.attributes.itervalues():
            attr.finalize(builder)

    def dump(self, context):
        with utils.XsdTagGuard('schema', context):
            if self.dom_element.target_ns is not None:
                context.add_attribute('targetNamespace',
                                      self.dom_element.target_ns)

            context.add_attribute('elementFormDefault',
                                  'qualified' if self.elements_qualified
                                  else 'unqualified')
            context.add_attribute('attributeFormDefault',
                                  'qualified' if self.attributes_qualified
                                  else 'unqualified')

            for c in self.children:
                c.dump(context)

    @staticmethod
    def _get_schema_location(attrs, builder, schema_path):
        try:
            location = builder.get_attribute(attrs, 'schemaLocation')
        except LookupError:
            location = None

        return _location2path(location, schema_path)

    @staticmethod
    def xsd_import(attrs, parent_element, builder,
                   schema_path, all_schemata):
        namespace = builder.get_attribute(attrs, 'namespace')

        new_schema_path = XsdSchema._get_schema_location(attrs, builder,
                                                         schema_path)

        if new_schema_path is not None:
            assert (os.path.isfile(new_schema_path) or
                    dumco.schema.checks.is_xml_namespace(namespace)), \
                'File {} does not exist'.format(new_schema_path)

            if os.path.isfile(new_schema_path):
                all_schemata[new_schema_path] = (
                    all_schemata[new_schema_path]
                    if new_schema_path in all_schemata else None)

        return (parent_element, {
            'annotation': builder.noop_handler,
        })

    @staticmethod
    def xsd_include(attrs, parent_element, builder,
                    schema_path, all_schemata):
        new_schema_path = XsdSchema._get_schema_location(attrs, builder,
                                                         schema_path)

        if new_schema_path is not None:
            assert os.path.isfile(new_schema_path), \
                'File {} does not exist'.format(new_schema_path)

            # Restart parsing with a new xsd.
            include_logic = _XsdIncludeLogic(schema_path, builder)
            xsd_root = include_logic.include_xml(schema_path)
            all_schemata[schema_path] = None
            builder.reset()

            raise dumco.schema.parsing.xml_parser.ParseRestart(
                StringIO.StringIO(xsd_root.toxml('utf-8')))

        return (parent_element, {
            'annotation': builder.noop_handler,
        })


class _XsdIncludeLogic(dumco.schema.parsing.xml_parser.IncludeLogic):
    def _is_xsd_node(self, node, name):
        return (node.nodeType == node.ELEMENT_NODE and
                dumco.schema.checks.is_xsd_namespace(node.namespaceURI) and
                node.localName == name)

    def _is_root_node(self, node):
        return self._is_xsd_node(node, 'schema')

    def _is_include_node(self, node):
        return self._is_xsd_node(node, 'include')

    def _get_included_path(self, node, curr_path):
        if node.hasAttribute('schemaLocation'):
            location = node.getAttribute('schemaLocation')

        return _location2path(location, curr_path)

    def _copy_included(self, including_dom, include_node,
                       included_root, included_path):
        including_root = including_dom.documentElement

        for node in included_root.childNodes:
            assert not self._is_include_node(node)

            new_node = including_dom.importNode(node, True)

            if self._is_xsd_node(node, 'import'):
                node_path = self._get_included_path(node, included_path)
                new_node.setAttribute('schemaLocation', node_path)

            including_root.insertBefore(new_node, include_node)

        including_root.removeChild(include_node)


def _location2path(location, schema_path):
    # Just ignore xml.xsd loading.
    if location == dumco.schema.xsd_types.XML_XSD_URI:
        location = None

    path = None
    if location is not None:
        path = os.path.realpath(
            os.path.join(os.path.dirname(schema_path), location))

    return path
