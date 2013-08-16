# Distributed under the GPLv2 License; see accompanying file COPYING.

from __future__ import print_function

import os.path
import shutil
import sys
import xml.sax.saxutils

import dumco.schema.base as base
import dumco.schema.checks as checks
import dumco.schema.elements as elements


_XSD_NS = 'xsd'
_XSD_URI = checks.XSD_NAMESPACE
_XML_NS = 'xml'
_VFILE_NS = 'dumco'


class _XmlWriter(object):
    ENTITIES = {chr(x): '&#{};'.format(x) for x in xrange(127, 256)}

    def __init__(self, filename):
        self.indentation = 0
        self.fhandle = None
        self.namespaces = {_XML_NS: checks.XML_NAMESPACE}
        self.complex_content = []
        self.prev_opened = False

        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        self.fhandle = open(filename, 'w')
        self.fhandle.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        self.fhandle.flush()

    def done(self):
        assert hasattr(self.fhandle, 'name')
        assert len(self.complex_content) == 0

        self.fhandle.flush()
        name = self.fhandle.name
        self.fhandle.close()

    def _indent(self):
        self.fhandle.write(' ' * self.indentation * 2)

    def open_tag(self, ns, uri, tag):
        if self.prev_opened:
            self.fhandle.write('>\n')
            self.complex_content[-1:] = [True]
        self.complex_content.append(False)
        self.prev_opened = True
        self._indent()
        self.fhandle.write('<{}:{}'.format(ns, tag))
        self.define_namespace(ns, uri)
        self.indentation += 1

    def close_tag(self, ns, uri, tag):
        self.indentation -= 1
        if self.complex_content[-1]:
            self._indent()
            self.fhandle.write('</{}:{}>\n'.format(ns, tag))
        else:
            self.fhandle.write('/>\n')
        self.complex_content.pop()
        self.prev_opened = False

    def define_namespace(self, ns, uri):
        if not ns in self.namespaces:
            self.namespaces[ns] = uri
            real_ns = '' if ns is None else (':{}'.format(ns))
            self.fhandle.write(' xmlns{}="{}"'.format(real_ns, uri))

    def add_attribute(self, name, value, ns=''):
        esc_value = xml.sax.saxutils.quoteattr(str(value), self.ENTITIES)
        if ns != '':
            self.fhandle.write(' {}:{}={}'.format(ns, name, esc_value))
        else:
            self.fhandle.write(' {}={}'.format(name, esc_value))

    def add_comment(self, comment):
        if self.prev_opened:
            self.fhandle.write('>\n')
            self.complex_content[-1:] = [True]
        self.prev_opened = False
        self._indent()
        self.fhandle.write('<!-- {} -->\n'.format(comment))


class _TagGuard(object):
    def __init__(self, tag, writer, ns=_XSD_NS, uri=_XSD_URI):
        self.ns = ns
        self.uri = uri
        self.tag = tag
        self.writer = writer

    def __enter__(self):
        self.writer.open_tag(self.ns, self.uri, self.tag)

    def __exit__(self, exc_type, exc_value, traceback):
        self.writer.close_tag(self.ns, self.uri, self.tag)


def _qname(name, own_schema, other_schema, ns=_XSD_NS):
    if own_schema != other_schema:
        prefix = ns
        if own_schema is not None:
            prefix = own_schema.prefix
        return '{}:{}'.format(prefix, name)
    return name


def _max_occurs(value):
    return ('unbounded' if value == base.UNBOUNDED else value)


def _dump_restriction(restriction, schema, xml_writer):
    with _TagGuard('restriction', xml_writer):
        xml_writer.add_attribute('base',
            _qname(restriction.base.name,
                   restriction.base.schema, schema))

        if restriction.enumeration:
            for e in restriction.enumeration:
                with _TagGuard('enumeration', xml_writer):
                    xml_writer.add_attribute('value', e[0])
        if restriction.length is not None:
            with _TagGuard('length', xml_writer):
                xml_writer.add_attribute('value', restriction.length)
        if restriction.max_exclusive is not None:
            with _TagGuard('maxExclusive', xml_writer):
                xml_writer.add_attribute('value', restriction.max_exclusive)
        if restriction.max_inclusive is not None:
            with _TagGuard('maxInclusive', xml_writer):
                xml_writer.add_attribute('value', restriction.max_inclusive)
        if restriction.max_length is not None:
            with _TagGuard('maxLength', xml_writer):
                xml_writer.add_attribute('value', restriction.max_length)
        if restriction.min_exclusive is not None:
            with _TagGuard('minExclusive', xml_writer):
                xml_writer.add_attribute('value', restriction.min_exclusive)
        if restriction.min_inclusive is not None:
            with _TagGuard('minInclusive', xml_writer):
                xml_writer.add_attribute('value', restriction.min_inclusive)
        if restriction.min_length is not None:
            with _TagGuard('minLength', xml_writer):
                xml_writer.add_attribute('value', restriction.min_length)
        if restriction.pattern is not None:
            with _TagGuard('pattern', xml_writer):
                xml_writer.add_attribute('value', restriction.pattern)


def _dump_listitem(listitem, schema, xml_writer):
    assert checks.is_primitive_type(listitem)

    with _TagGuard('list', xml_writer):
        xml_writer.add_attribute('listItem',
            _qname(listitem.name, listitem.schema, schema))


def _dump_union(union, schema, xml_writer):
    assert all([checks.is_primitive_type(m) for m in union])

    with _TagGuard('union', xml_writer):
        xml_writer.add_attribute('memberItems',
            ' '.join([_qname(m.name, m.schema, schema) for m in union]))


def _dump_simple_content(cont, attrs, schema, xml_writer):
    with _TagGuard('simpleContent', xml_writer):
        with _TagGuard('restriction', xml_writer):
            xml_writer.add_attribute('base',
                _qname(cont.type.name, cont.type.schema, schema))

            for a in attrs:
                if checks.is_any(a.attribute):
                    with _TagGuard('anyAttribute', xml_writer):
                        _dump_any(a.attribute, schema, xml_writer)
                else:
                    _dump_attribute(a, schema, xml_writer)


def _dump_particle(particle, schema, xml_writer, names):
    name = particle.term.__class__.__name__.lower()
    with _TagGuard(name, xml_writer):
        if checks.is_compositor(particle.term):
            xml_writer.add_attribute('name', particle.name, ns=_VFILE_NS)
        elif checks.is_element(particle.term):
            _dump_element_attributes(particle.term, schema, xml_writer)

        if particle.min_occurs != 1:
            xml_writer.add_attribute('minOccurs', particle.min_occurs)
        if particle.max_occurs != 1:
            xml_writer.add_attribute('maxOccurs',
                                     _max_occurs(particle.max_occurs))

        if checks.is_compositor(particle.term):
            for p in particle.term.particles:
                _dump_particle(p, schema, xml_writer, names)
        elif checks.is_element(particle.term):
            pass
        elif checks.is_any(particle.term):
            _dump_any(particle.term, schema, xml_writer)
        else: # pragma: no cover
            assert False


def _dump_attribute(attr, schema, xml_writer):
    assert (checks.is_attribute(attr.attribute) or
            checks.is_xmlattribute(attr.attribute))

    with _TagGuard('attribute', xml_writer):
        _dump_attribute_attributes(attr.attribute, schema, xml_writer)

        if attr.default is not None:
            xml_writer.add_attribute('default', attr.default)

        if attr.required:
            xml_writer.add_attribute('use', 'required')


def _dump_attribute_attributes(attr, schema, xml_writer, top_level=False):
    attrs = []
    if not checks.is_xmlattribute(attr):
        attrs = [a.attribute for a in attr.schema.attributes.itervalues()]
    if top_level or (not checks.is_xmlattribute(attr) and
                     attr.schema == schema and attr not in attrs):
        xml_writer.add_attribute('name',
            _qname(attr.name, attr.schema, schema))
        if not checks.is_simple_urtype(attr.type):
            xml_writer.add_attribute('type',
                _qname(attr.type.name, attr.type.schema, schema))

        xml_writer.add_attribute('form',
            'qualified' if attr.qualified else 'unqualified')
    else:
        ns = _XSD_NS
        if checks.is_xmlattribute(attr):
            ns = _XML_NS
        xml_writer.add_attribute('ref',
            _qname(attr.name, attr.schema, schema, ns=ns))


def _dump_element_attributes(elem, schema, xml_writer, top_level=False):
    assert checks.is_element(elem)

    elems = [p.term for p in elem.schema.elements.itervalues()]
    if top_level or (elem.schema is not None and
                     elem.schema == schema and elem not in elems):
        xml_writer.add_attribute('name',
            _qname(elem.name, elem.schema, schema))
        if not checks.is_complex_urtype(elem.type):
            xml_writer.add_attribute('type',
                _qname(elem.type.name, elem.type.schema, schema))

        xml_writer.add_attribute('form',
            'qualified' if elem.qualified else 'unqualified')
    else:
        xml_writer.add_attribute('ref',
            _qname(elem.name, elem.schema, schema))


def _dump_any(elem, schema, xml_writer):
    assert checks.is_any(elem)

    val = elem.namespace
    if isinstance(elem.namespace, list):
        val = ' '.join(elem.namespace)
    elif elem.namespace == elements.Any.ANY:
        val = '##any'
    elif elem.namespace == elements.Any.OTHER:
        val = '##other'

    xml_writer.add_attribute('namespace', val)


def dump_xsd(schemata, output_dir):
    print('Dumping XML Schema files to {}...'.format(
        os.path.realpath(output_dir)))

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    for (schema_file, schema) in schemata.iteritems():
        file_path = os.path.join(output_dir, os.path.basename(schema_file))
        file_path = '{}.xsd'.format(file_path.rpartition('.')[0])

        xml_writer = _XmlWriter(file_path)
        with _TagGuard('schema', xml_writer):
            xml_writer.add_attribute('targetNamespace', schema.target_ns)

            xml_writer.define_namespace(_VFILE_NS, 'http://dumco.com/naming')
            for (ns, uri) in schema.namespaces.iteritems():
                xml_writer.define_namespace(ns, uri)

            if len(schema.imports) != 0:
                xml_writer.add_comment('Imports')
            for (ns, sub_schema) in schema.imports.iteritems():
                with _TagGuard('import', xml_writer):
                    xml_writer.add_attribute('namespace', ns)
                    xml_writer.add_attribute('schemaLocation',
                                             os.path.basename(sub_schema.path))

            if len(schema.simple_types) != 0:
                xml_writer.add_comment('Simple Types')
            for (name, st) in sorted(schema.simple_types.iteritems(),
                                     key=lambda item: item[0]):
                with _TagGuard('simpleType', xml_writer):
                    xml_writer.add_attribute('name', name)

                    if st.restriction is not None:
                        _dump_restriction(st.restriction, schema, xml_writer)
                    elif st.listitem is not None:
                        _dump_listitem(st.listitem, schema, xml_writer)
                    elif st.union:
                        _dump_union(st.union, schema, xml_writer)

            if len(schema.complex_types) != 0:
                xml_writer.add_comment('Complex Types')
            for (name, ct) in sorted(schema.complex_types.iteritems(),
                                     key=lambda item: item[0]):
                with _TagGuard('complexType', xml_writer):
                    xml_writer.add_attribute('name', name)
                    if ct.mixed:
                        xml_writer.add_attribute('mixed', ct.mixed)

                    if checks.has_simple_content(ct):
                        _dump_simple_content(ct.text, ct.attributes,
                                             schema, xml_writer)
                    elif (ct.mixed or
                          checks.has_complex_content(ct)):
                        _dump_particle(ct.particle, schema, xml_writer, set())

                    if not checks.has_simple_content(ct):
                        for a in ct.attributes:
                            if checks.is_any(a.attribute):
                                with _TagGuard('anyAttribute', xml_writer):
                                    _dump_any(a.attribute, schema, xml_writer)
                            else:
                                _dump_attribute(a, schema, xml_writer)

            if len(schema.elements) != 0:
                xml_writer.add_comment('Elements')
            for (name, elem) in sorted(schema.elements.iteritems(),
                                       key=lambda item: item[0]):
                with _TagGuard('element', xml_writer):
                    _dump_element_attributes(elem.term, schema, xml_writer,
                                             top_level=True)

            if len(schema.attributes) != 0:
                xml_writer.add_comment('Attributes')
            for (name, attr) in sorted(schema.attributes.iteritems(),
                                       key=lambda item: item[0]):
                with _TagGuard('attribute', xml_writer):
                    _dump_attribute_attributes(attr.attribute, schema,
                                               xml_writer, top_level=True)

        xml_writer.done()
