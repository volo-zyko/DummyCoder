# Distributed under the GPLv2 License; see accompanying file COPYING.

import copy
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

    for (prefix, uri) in factory.namespaces.iteritems():
        schema.schema_element.set_namespace(prefix, uri)

    if (factory.current_xsd is None or
        (not isinstance(factory.current_xsd, StringIO.StringIO) and
         factory.current_xsd != schema_path)):
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

    @staticmethod
    def _get_schema_location(attrsOrNode, factory, schema_path):
        location = None

        if isinstance(attrsOrNode, xml.dom.minidom.Element):
            if attrsOrNode.hasAttribute('schemaLocation'):
                location = attrsOrNode.getAttribute('schemaLocation')
        else:
            try:
                location = factory.get_attribute(attrsOrNode, 'schemaLocation')
            except LookupError:
                pass

        # Just ignore xml.xsd loading.
        if location == dumco.schema.checks.XML_XSD_URI:
            location = None

        path = None
        if location is not None:
            path = os.path.realpath(
                os.path.join(os.path.dirname(schema_path), location))

        return (location, path)

    @staticmethod
    def xsd_import(attrs, parent_element, factory,
                   schema_path, all_schemata):
        namespace = factory.get_attribute(attrs, 'namespace')

        (_, new_schema_path) = XsdSchema._get_schema_location(attrs, factory,
                                                              schema_path)

        if new_schema_path is not None:
            assert (os.path.isfile(new_schema_path) or
                    namespace == dumco.schema.checks.XML_NAMESPACE), \
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
        (location, new_schema_path) = \
            XsdSchema._get_schema_location(attrs, factory, schema_path)

        if new_schema_path is not None:
            assert os.path.isfile(new_schema_path), \
                'File {} does not exist'.format(new_schema_path)

            if os.path.isfile(new_schema_path):
                factory.included_schema_paths.add(new_schema_path)

                string_stream = _merge_xsds(factory.current_xsd, schema_path,
                                            new_schema_path, location, factory)

                # Restart parsing with a new xsd.
                factory.reset()
                factory.current_xsd = copy.copy(string_stream)
                all_schemata[schema_path] = None
                raise dumco.xml.parser.ParseRestart(string_stream)

        return (parent_element, {
            'annotation': factory.noop_handler,
        })


def _merge_xsds(curr_document, curr_path, new_path, location, factory):
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

        (l, _) = XsdSchema._get_schema_location(n, factory, curr_path)
        if l is not None and l == location:
            found_include = True
            orig_root.removeChild(n)
            break

    assert found_include, 'Cannot find include for removal'

    # Copy components from included xsd to including xsd.
    for n in new_root.childNodes:
        new = orig_dom.importNode(n, True)

        if is_schema_node(new, 'include'):
            (_, path) = XsdSchema._get_schema_location(n, factory, new_path)
            new.setAttribute('schemaLocation', path)

        if is_schema_node(new, 'import'):
            (_, path) = XsdSchema._get_schema_location(n, factory, new_path)
            new.setAttribute('schemaLocation', path)

        orig_root.appendChild(new)

    # Copy namespace declarations.
    for a in [new_root.attributes.item(i)
              for i in xrange(0, new_root.attributes.length)]:
        if a.name.startswith('xmlns:') and not orig_root.hasAttribute(a.name):
            orig_root.setAttribute(a.name, a.value)

    return StringIO.StringIO(orig_dom.toxml('utf-8'))
