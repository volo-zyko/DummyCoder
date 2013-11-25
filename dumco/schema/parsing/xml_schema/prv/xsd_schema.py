# Distributed under the GPLv2 License; see accompanying file COPYING.

import os.path
import StringIO
import xml.dom.minidom

from dumco.utils.decorators import method_once

import dumco.schema.checks
import dumco.schema.elements
import dumco.schema.namer

import dumco.schema.parsing.xml_parser

import xsd_attribute
import xsd_attribute_group
import xsd_base
import xsd_complex_type
import xsd_element
import xsd_group
import xsd_simple_type


def xsd_schema(attrs, parent_element, factory, schema_path, all_schemata):
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


class XsdSchema(xsd_base.XsdBase):
    def __init__(self, attrs, schema_path):
        super(XsdSchema, self).__init__(attrs)

        self.path = schema_path

        self.attributes_qualified = \
            self.attr('attributeFormDefault') == 'qualified'
        self.elements_qualified = \
            self.attr('elementFormDefault') == 'qualified'

        self.schema_element = dumco.schema.elements.Schema(
            self.attr('targetNamespace'))
        assert schema_path.endswith('.xsd')
        self.schema_element.filename = \
            os.path.basename(schema_path).rpartition('.')[0]

        self.attributes = {}
        self.attribute_groups = {}
        self.complex_types = {}
        self.elements = {}
        self.groups = {}
        self.imports = {}
        self.simple_types = {}
        self.unnamed_types = []

    def set_imports(self, all_schemata, factory):
        self.imports = {}

        for path in all_schemata.iterkeys():
            if any([(path in included_paths) for included_paths
                    in factory.included_schema_paths.itervalues()]):
                continue

            schema = all_schemata[path]

            assert schema.schema_element.target_ns not in self.imports, \
                'Attempting to redefine imported schema for {}'.format(
                    schema.schema_element.target_ns)

            self.imports[schema.schema_element.target_ns] = schema

    @method_once
    def finalize(self, all_schemata, factory):
        forged_names = dumco.schema.namer.ValidatingNameSet()
        schema_element = self.schema_element

        for name in sorted(self.simple_types.iterkeys()):
            schema_st = self.simple_types[name].finalize(factory)
            schema_st.nameit([self], factory.namer, forged_names)
            schema_element.simple_types.append(schema_st)

        for name in sorted(self.complex_types.iterkeys()):
            schema_ct = self.complex_types[name].finalize(factory)
            schema_ct.nameit([self], factory.namer, forged_names)
            schema_element.complex_types.append(schema_ct)

        for (parents, t) in sorted(self.unnamed_types,
                                   key=lambda x: len(x[0])):
            schema_type = t.finalize(factory)
            schema_type.nameit(parents, factory.namer, forged_names)

            if dumco.schema.checks.is_complex_type(schema_type):
                schema_element.complex_types.append(schema_type)
            elif dumco.schema.checks.is_simple_type(schema_type):
                schema_element.simple_types.append(schema_type)

        for elem in self.elements.itervalues():
            particle = elem.finalize(factory)
            schema_element.elements.append(particle.term)

        for attr in self.attributes.itervalues():
            attr_use = attr.finalize(factory)
            schema_element.attributes.append(attr_use.attribute)

        schema_element.simple_types.sort(key=lambda st: st.name)
        schema_element.complex_types.sort(key=lambda ct: ct.name)
        schema_element.elements.sort(key=lambda e: e.name)
        schema_element.attributes.sort(key=lambda a: a.name)

    @staticmethod
    def _get_schema_location(attrs_or_node, factory, schema_path):
        location = None

        if isinstance(attrs_or_node, xml.dom.minidom.Element):
            if attrs_or_node.hasAttribute('schemaLocation'):
                location = attrs_or_node.getAttribute('schemaLocation')
        else:
            try:
                location = factory.get_attribute(attrs_or_node,
                                                 'schemaLocation')
            except LookupError:
                pass

        # Just ignore xml.xsd loading.
        if location == dumco.schema.base.XML_XSD_URI:
            location = None

        path = None
        if location is not None:
            path = os.path.realpath(
                os.path.join(os.path.dirname(schema_path), location))

        return path

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
            xsd_root = _include_xsds(schema_path, schema_path, factory)
            all_schemata[schema_path] = None
            factory.reset()

            raise dumco.schema.parsing.xml_parser.ParseRestart(
                StringIO.StringIO(xsd_root.toxml('utf-8')))

        return (parent_element, {
            'annotation': factory.noop_handler,
        })


def _include_xsds(schema_path, curr_path, factory):
    def is_schema_node(node, name):
        return (node.nodeType == node.ELEMENT_NODE and
            dumco.schema.checks.is_xsd_namespace(node.namespaceURI) and
            node.localName == name)

    orig_dom = xml.dom.minidom.parse(curr_path)
    orig_root = orig_dom.documentElement

    assert is_schema_node(orig_root, 'schema'), 'Not a schema document'

    for n in list(orig_root.childNodes):
        if not is_schema_node(n, 'include'):
            continue

        n_path = XsdSchema._get_schema_location(n, factory, curr_path)
        if n_path is None:
            continue

        orig_root.removeChild(n)

        included_paths = \
            factory.included_schema_paths.setdefault(schema_path, set())
        if n_path in factory.included_schema_paths or n_path in included_paths:
            continue
        included_paths.add(n_path)

        n_dom = _include_xsds(schema_path, n_path, factory)
        n_root = n_dom.documentElement

        # Copy components from included xsd to including xsd.
        for m in n_root.childNodes:
            assert not is_schema_node(m, 'include')

            m_new = orig_dom.importNode(m, True)

            if is_schema_node(m, 'import'):
                m_path = XsdSchema._get_schema_location(m, factory, n_path)
                m_new.setAttribute('schemaLocation', m_path)

            orig_root.appendChild(m_new)

        # Copy namespace declarations.
        for i in xrange(0, n_root.attributes.length):
            a = n_root.attributes.item(i)
            if (a.name.startswith('xmlns:') and
                not orig_root.hasAttribute(a.name)):
                orig_root.setAttribute(a.name, a.value)

    return orig_dom
