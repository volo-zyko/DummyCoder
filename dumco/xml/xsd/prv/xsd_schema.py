# Distributed under the GPLv2 License; see accompanying file COPYING.

import os.path
import StringIO
import xml.dom.minidom

from dumco.utils.decorators import method_once

import dumco.schema.checks
import dumco.schema.elements
import dumco.schema.namer

import dumco.xml.parser

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

    if factory.current_xsd is None:
        factory.current_xsd = schema_path

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
        self.simple_types = {}
        self.unnamed_types = []

    def set_imports(self, all_schemata):
        self.imports = {
            all_schemata[path].schema_element.target_ns: all_schemata[path]
            for path in self.imports.iterkeys()}

    @method_once
    def finalize(self, all_schemata, factory):
        forged_names = dumco.schema.namer.ValidatingNameSet()
        schema_element = self.schema_element

        for name in sorted(self.simple_types.iterkeys()):
            schema_st = self.simple_types[name].finalize(factory)
            schema_st.nameit([self], factory.namer, forged_names)
            schema_element.simple_types[schema_st.name] = schema_st

        for name in sorted(self.complex_types.iterkeys()):
            schema_ct = self.complex_types[name].finalize(factory)
            schema_ct.nameit([self], factory.namer, forged_names)
            schema_element.complex_types[schema_ct.name] = schema_ct

        for (parents, t) in sorted(self.unnamed_types,
                                   key=lambda x: len(x[0])):
            schema_type = t.finalize(factory)
            schema_type.nameit(parents, factory.namer, forged_names)

            if dumco.schema.checks.is_complex_type(schema_type):
                schema_element.complex_types[schema_type.name] = schema_type
            elif dumco.schema.checks.is_simple_type(schema_type):
                schema_element.simple_types[schema_type.name] = schema_type

        for elem in self.elements.itervalues():
            schema_elem = elem.finalize(factory)
            name = schema_elem.term.name
            schema_element.elements[name] = schema_elem.term

        for attr in self.attributes.itervalues():
            schema_attr_use = attr.finalize(factory)
            name = schema_attr_use.attribute.name
            schema_element.attribute_uses[name] = schema_attr_use

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
        if location == dumco.schema.checks.XML_XSD_URI:
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
                all_schemata[schema_path].imports[new_schema_path] = None

        return (parent_element, {
            'annotation': factory.noop_handler,
        })

    @staticmethod
    def xsd_include(attrs, parent_element, factory,
                    schema_path, all_schemata):
        new_schema_path = \
            XsdSchema._get_schema_location(attrs, factory, schema_path)

        if new_schema_path is not None:
            assert os.path.isfile(new_schema_path), \
                'File {} does not exist'.format(new_schema_path)

            inc_paths = \
                factory.included_schema_paths.setdefault(schema_path, set())
            if (os.path.isfile(new_schema_path) and
                new_schema_path not in inc_paths and
                new_schema_path not in factory.included_schema_paths):
                inc_paths.add(new_schema_path)

                current_xsd_copy = factory.current_xsd
                if isinstance(current_xsd_copy, StringIO.StringIO):
                    # Copy StringIO so that in a new stream we start
                    # reading from the beginning.
                    current_xsd_copy = \
                        StringIO.StringIO(factory.current_xsd.getvalue())

                # Restart parsing with a new xsd.
                factory.current_xsd = _merge_xsds(current_xsd_copy, schema_path,
                                                  new_schema_path, factory)
                all_schemata[schema_path] = None
                factory.reset()

                raise dumco.xml.parser.ParseRestart(factory.current_xsd)

        return (parent_element, {
            'annotation': factory.noop_handler,
        })


def _merge_xsds(curr_document, curr_path, new_path, factory):
    orig_dom = xml.dom.minidom.parse(curr_document)
    new_dom = xml.dom.minidom.parse(new_path)

    orig_root = orig_dom.documentElement
    new_root = new_dom.documentElement

    def is_schema_node(node, name):
        return (node.nodeType == node.ELEMENT_NODE and
            dumco.schema.checks.is_xsd_namespace(node.namespaceURI) and
            node.localName == name)

    assert is_schema_node(orig_root, 'schema'), 'Not a schema document'
    assert is_schema_node(new_root, 'schema'), 'Not a schema document'

    # Find the right include directive and remove it from original xsd.
    found_include = False
    for n in orig_root.childNodes:
        if not is_schema_node(n, 'include'):
            continue

        path = XsdSchema._get_schema_location(n, factory, curr_path)
        if path is not None and path == new_path:
            found_include = True
            orig_root.removeChild(n)
            break

    assert found_include, 'Cannot find include {} for removal'.format(new_path)

    # Copy components from included xsd to including xsd.
    for n in new_root.childNodes:
        new = orig_dom.importNode(n, True)

        if is_schema_node(new, 'include'):
            path = XsdSchema._get_schema_location(n, factory, new_path)
            new.setAttribute('schemaLocation', path)

        if is_schema_node(new, 'import'):
            path = XsdSchema._get_schema_location(n, factory, new_path)
            new.setAttribute('schemaLocation', path)

        orig_root.appendChild(new)

    # Copy namespace declarations.
    for a in [new_root.attributes.item(i)
              for i in xrange(0, new_root.attributes.length)]:
        if a.name.startswith('xmlns:') and not orig_root.hasAttribute(a.name):
            orig_root.setAttribute(a.name, a.value)

    return StringIO.StringIO(orig_dom.toxml('utf-8'))
