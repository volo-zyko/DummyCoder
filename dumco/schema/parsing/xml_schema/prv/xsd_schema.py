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
import xsd_attribute
import xsd_attribute_group
import xsd_complex_type
import xsd_element
import xsd_group
import xsd_simple_type


def xsd_schema(attrs, parent_element, factory, schema_path, all_schemata):
    if dumco.schema.checks.is_xml_namespace(attrs.get('targetNamespace', None)):
        del all_schemata[schema_path]
        factory.reset()

        raise dumco.schema.parsing.xml_parser.SkipParse()

    schema = XsdSchema(attrs, schema_path)
    all_schemata[schema_path] = schema

    return (schema, {
        'annotation': factory.noop_handler,
        'attribute': xsd_attribute.xsd_attribute,
        'attributeGroup': xsd_attribute_group.xsd_attributeGroup,
        'complexType': xsd_complex_type.xsd_complexType,
        'element': xsd_element.xsd_element,
        'group': xsd_group.xsd_group,
        'import': XsdSchema.xsd_import,
        'include': XsdSchema.xsd_include,
        'notation': factory.noop_handler,
        'redefine': factory.noop_handler,
        'simpleType': xsd_simple_type.xsd_simpleType,
    })


class XsdSchema(base.XsdBase):
    def __init__(self, attrs, schema_path):
        super(XsdSchema, self).__init__(attrs)

        self.path = schema_path

        self.attributes_qualified = \
            self.attr('attributeFormDefault') == 'qualified'
        self.elements_qualified = \
            self.attr('elementFormDefault') == 'qualified'

        self.schema_element = dumco.schema.model.Schema(
            self.attr('targetNamespace'))
        assert schema_path.endswith('.xsd')
        self.schema_element.filename = \
            os.path.splitext(os.path.basename(schema_path))[0]

        self.attributes = {}
        self.attribute_groups = {}
        self.complex_types = {}
        self.elements = {}
        self.groups = {}
        self.imports = {}
        self.simple_types = {}
        self.unnamed_types = []

    def set_imports(self, all_schemata, factory):
        for path in all_schemata.iterkeys():
            if any([(path in included_paths) for included_paths in
                    factory.included_schema_paths.itervalues()]):
                continue

            schema = all_schemata[path]

            assert schema.schema_element.target_ns not in self.imports, \
                'Attempting to redefine imported schema for {}'.format(
                    schema.schema_element.target_ns)

            self.imports[schema.schema_element.target_ns] = schema

    @method_once
    def finalize(self, all_schemata, factory):
        key_extractor = lambda x: x.schema_element.name

        for st in sorted(self.simple_types.itervalues(), key=key_extractor):
            st.finalize(factory)

        for ct in sorted(self.complex_types.itervalues(), key=key_extractor):
            ct.finalize(factory)

        for xsd_type in self.unnamed_types:
            xsd_type.finalize(factory)

        for elem in self.elements.itervalues():
            particle = elem.finalize(factory)
            self.schema_element.elements.append(particle.term)

        for attr in self.attributes.itervalues():
            attr.finalize(factory)

    @staticmethod
    def _get_schema_location(attrs, factory, schema_path):
        try:
            location = factory.get_attribute(attrs, 'schemaLocation')
        except LookupError:
            location = None

        return _location2path(location, schema_path)

    @staticmethod
    def xsd_import(attrs, parent_element, factory,
                   schema_path, all_schemata):
        namespace = factory.get_attribute(attrs, 'namespace')

        new_schema_path = XsdSchema._get_schema_location(attrs, factory,
                                                         schema_path)

        if new_schema_path is not None:
            assert (os.path.isfile(new_schema_path) or
                    dumco.schema.checks.is_xml_namespace(namespace)), \
                'File {} does not exist'.format(new_schema_path)

            if os.path.isfile(new_schema_path):
                all_schemata[new_schema_path] = all_schemata[new_schema_path] \
                    if new_schema_path in all_schemata else None

        return (parent_element, {
            'annotation': factory.noop_handler,
        })

    @staticmethod
    def xsd_include(attrs, parent_element, factory,
                    schema_path, all_schemata):
        new_schema_path = XsdSchema._get_schema_location(attrs, factory,
                                                         schema_path)

        if new_schema_path is not None:
            assert os.path.isfile(new_schema_path), \
                'File {} does not exist'.format(new_schema_path)

            # Restart parsing with a new xsd.
            include_logic = _XsdIncludeLogic(schema_path, factory)
            xsd_root = include_logic.include_xml(schema_path)
            all_schemata[schema_path] = None
            factory.reset()

            raise dumco.schema.parsing.xml_parser.ParseRestart(
                StringIO.StringIO(xsd_root.toxml('utf-8')))

        return (parent_element, {
            'annotation': factory.noop_handler,
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
