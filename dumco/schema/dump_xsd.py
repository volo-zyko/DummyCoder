# Distributed under the GPLv2 License; see accompanying file COPYING.

import collections
import functools
import os.path
import shutil

import dumco.utils.string_utils

import base
import checks
import elements
import enums
import xsd_types
import uses


_XSD_PREFIX = 'xsd'
_XML_PREFIX = 'xml'
_XSD_NAMESPACE = xsd_types.XSD_NAMESPACE
_XML_XSD_URI = xsd_types.XML_XSD_URI


class _XmlWritingContext(object):
    def __init__(self, filename, opacity_manager):
        self.om = opacity_manager
        self.indentation = 0
        self.fhandle = None
        self.namespaces = {_XML_PREFIX: base.XML_NAMESPACE}
        self.complex_content = []
        self.prev_opened = False

        # We track here attribute and element groups.
        # In this case XmlWriter is used as global object.
        self.elements = None
        self.ctypes = None
        self.stypes = None
        self.agroups = None
        self.egroups = None
        self.imports = None

        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        self.fhandle = open(filename, 'w')
        self.fhandle.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        self.fhandle.flush()

    def done(self):
        assert hasattr(self.fhandle, 'name')
        assert len(self.complex_content) == 0

        self.fhandle.flush()
        self.fhandle.close()

    def _indent(self):
        self.fhandle.write(' ' * self.indentation * 2)

    def open_tag(self, prefix, uri, tag):
        if self.prev_opened:
            self.fhandle.write('>\n')
            self.complex_content[-1:] = [True]
        self.complex_content.append(False)
        self.prev_opened = True
        self._indent()
        self.fhandle.write('<{}:{}'.format(prefix, tag))
        self.define_namespace(prefix, uri)
        self.indentation += 1

    def close_tag(self, prefix, uri, tag):
        self.indentation -= 1
        if self.complex_content[-1]:
            self._indent()
            self.fhandle.write('</{}:{}>\n'.format(prefix, tag))
        else:
            self.fhandle.write('/>\n')
        self.complex_content.pop()
        self.prev_opened = False

    def define_namespace(self, prefix, uri):
        if not prefix in self.namespaces:
            self.namespaces[prefix] = uri
            real_prefix = '' if prefix is None else (':{}'.format(prefix))
            self.fhandle.write(' xmlns{}="{}"'.format(real_prefix, uri))

    def add_attribute(self, name, value, prefix=''):
        esc_value = dumco.utils.string_utils.quote_xml_attribute(value)
        if prefix != '':
            self.fhandle.write(' {}:{}={}'.format(prefix, name, esc_value))
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
    def __init__(self, tag, writer, prefix=_XSD_PREFIX, uri=_XSD_NAMESPACE):
        self.prefix = prefix
        self.uri = uri
        self.tag = tag
        self.writer = writer

    def __enter__(self):
        self.writer.open_tag(self.prefix, self.uri, self.tag)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.writer.close_tag(self.prefix, self.uri, self.tag)
        return exc_value is None


def _qname(name, own_schema, other_schema, prefix=_XSD_PREFIX):
    if own_schema != other_schema:
        return '{}:{}'.format(
            own_schema.prefix if own_schema is not None else prefix, name)
    return name


def _max_occurs(value):
    return ('unbounded' if value == base.UNBOUNDED else value)


def _term_name(term):
    if checks.is_interleave(term):
        return 'all'
    return term.__class__.__name__.lower()


def _dump_restriction(restriction, schema, xml_writer):
    with _TagGuard('restriction', xml_writer):
        xml_writer.add_attribute(
            'base',
            _qname(restriction.base.name, restriction.base.schema, schema))

        if restriction.enumeration:
            for e in restriction.enumeration:
                with _TagGuard('enumeration', xml_writer):
                    xml_writer.add_attribute('value', e.value)
        if restriction.fraction_digits is not None:
            with _TagGuard('fractionDigits', xml_writer):
                xml_writer.add_attribute('value', restriction.fraction_digits)
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
        if restriction.total_digits is not None:
            with _TagGuard('totalDigits', xml_writer):
                xml_writer.add_attribute('value', restriction.total_digits)
        if restriction.white_space is not None:
            if restriction.white_space == elements.Restriction.WS_PRESERVE:
                value = 'preserve'
            elif restriction.white_space == elements.Restriction.WS_REPLACE:
                value = 'replace'
            elif restriction.white_space == elements.Restriction.WS_COLLAPSE:
                value = 'collapse'
            with _TagGuard('whiteSpace', xml_writer):
                xml_writer.add_attribute('value', value)


def _dump_listitems(listitems, schema, xml_writer):
    assert len(listitems) == 1, 'Cannot dump xs:list'

    with _TagGuard('list', xml_writer):
        xml_writer.add_attribute(
            'itemType',
            _qname(listitems[0].type.name, listitems[0].type.schema, schema))


def _dump_union(union, schema, xml_writer):
    assert all([checks.is_primitive_type(m) for m in union])

    with _TagGuard('union', xml_writer):
        xml_writer.add_attribute(
            'memberTypes',
            ' '.join([_qname(m.name, m.schema, schema) for m in union]))


def _dump_simple_content(ct, schema, xml_writer):
    with _TagGuard('simpleContent', xml_writer):
        with _TagGuard('extension', xml_writer):
            qn = _qname(ct.text().type.name,
                        ct.text().type.schema, schema)
            xml_writer.add_attribute('base', qn)

            _dump_attribute_uses(ct, ct.attribute_uses(), schema, xml_writer)


def _dump_particle(ct, particle, schema, xml_writer, names, in_group=False):
    def dump_occurs_attributes():
        if particle.min_occurs != 1:
            xml_writer.add_attribute('minOccurs', particle.min_occurs)
        if particle.max_occurs != 1:
            xml_writer.add_attribute('maxOccurs',
                                     _max_occurs(particle.max_occurs))

    if not checks.is_particle(particle):
        return
    elif particle.term.schema != schema:
        groups = xml_writer.egroups.get(particle.term.schema, {})

        if particle.term in [t for t in groups.iterkeys()]:
            group_name = groups[particle.term].name
            with _TagGuard('group', xml_writer):
                xml_writer.add_attribute(
                    'ref',
                    _qname(group_name, particle.term.schema, schema))

                dump_occurs_attributes()

            return

    if (checks.is_element(particle.term) and
            xml_writer.om.is_opaque_ct_member(ct, particle.term)):
        return
    elif (checks.is_compositor(particle.term) and
            all([xml_writer.om.is_opaque_ct_member(ct, p.term)
                 for p in particle.traverse() if checks.is_particle(p)])):
        return

    name = _term_name(particle.term)
    with _TagGuard(name, xml_writer):
        if not in_group:
            dump_occurs_attributes()

        if checks.is_compositor(particle.term):
            for p in particle.term.members:
                _dump_particle(ct, p, schema, xml_writer, names)
        elif checks.is_element(particle.term):
            is_element_def = False
            if particle.term.schema == schema:
                top_elements = [e for e in particle.term.schema.elements]

                is_element_def = particle.term not in top_elements

            _dump_element_attributes(particle.term, is_element_def,
                                     schema, xml_writer)

            if is_element_def:
                xml_writer.add_attribute(
                    'form',
                    'qualified' if particle.qualified else 'unqualified')
        elif checks.is_any(particle.term):
            _dump_any(particle.term, schema, xml_writer)
        else:  # pragma: no cover
            assert False


def _dump_attribute_uses(ct, attr_uses, schema, xml_writer):
    for u in attr_uses:
        if (xml_writer.om.is_opaque_ct_member(ct, u.attribute) and
                not checks.is_single_valued_type(ct)):
            continue

        if checks.is_any(u.attribute):
            with _TagGuard('anyAttribute', xml_writer):
                _dump_any(u.attribute, schema, xml_writer)
        else:
            _dump_attribute_use(u, schema, xml_writer)


def _dump_attribute_use(attr_use, schema, xml_writer):
    assert checks.is_attribute(attr_use.attribute)

    attribute = attr_use.attribute

    if not checks.is_xml_attribute(attribute) and attribute.schema != schema:
        # We reference attribute from other schema but since we don't
        # maintain top-level attributes we can reference then only
        # attribute group.
        groups = xml_writer.agroups[attribute.schema]
        group_name = groups[attribute].name
        with _TagGuard('attributeGroup', xml_writer):
            xml_writer.add_attribute(
                'ref',
                _qname(group_name, attribute.schema, schema))

        return

    with _TagGuard('attribute', xml_writer):
        if checks.is_xml_attribute(attribute):
            xml_writer.add_attribute('ref', _qname(
                attribute.name, attribute.schema, schema, prefix=_XML_PREFIX))
        else:
            _dump_attribute_attributes(attribute, schema, xml_writer)

        xml_writer.add_attribute(
            'form',
            'qualified' if attr_use.qualified else 'unqualified')

        if attr_use.constraint.fixed:
            assert attr_use.constraint.value is not None, \
                'Attribute has fixed value but the value itself is unknown'
            xml_writer.add_attribute('fixed',
                                     attr_use.constraint.value)
        elif attr_use.constraint.value is not None:
            xml_writer.add_attribute('default',
                                     attr_use.constraint.value)

        if attr_use.required:
            xml_writer.add_attribute('use', 'required')


def _dump_attribute_attributes(attribute, schema, xml_writer):
    assert checks.is_attribute(attribute)

    xml_writer.add_attribute(
        'name',
        _qname(attribute.name, attribute.schema, schema))

    if not checks.is_simple_urtype(attribute.type):
        xml_writer.add_attribute(
            'type',
            _qname(attribute.type.name, attribute.type.schema, schema))


def _dump_element_attributes(element, is_element_definition,
                             schema, xml_writer):
    assert checks.is_element(element)

    if is_element_definition:
        xml_writer.add_attribute(
            'name',
            _qname(element.name, element.schema, schema))

        if (not checks.is_complex_urtype(element.type) and
                not checks.is_simple_urtype(element.type)):
            xml_writer.add_attribute(
                'type',
                _qname(element.type.name, element.type.schema, schema))

        if element.constraint.fixed:
            assert element.constraint.value, \
                'Element has fixed value but the value itself is unknown'
            xml_writer.add_attribute('fixed',
                                     element.constraint.value)
        elif element.constraint.value is not None:
            xml_writer.add_attribute('default',
                                     element.constraint.value)
    else:
        xml_writer.add_attribute(
            'ref',
            _qname(element.name, element.schema, schema))


def _dump_any(elem, schema, xml_writer):
    assert checks.is_any(elem)

    val = '##any'
    if not elem.constraints:
        val = '##any'
    elif (len(elem.constraints) == 1 and
          isinstance(elem.constraints[0], elements.Any.Not) and
          isinstance(elem.constraints[0].name, elements.Any.Name) and
          elem.constraints[0].name.ns == schema.target_ns and
          elem.constraints[0].name.tag is None):
        val = '##other'
    elif (len(elem.constraints) > 1 and
          all([isinstance(x, elements.Any.Name) and x.tag is None
               for x in elem.constraints])):
        val = ' '.join([x.ns for x in elem.constraints])
    else:
        # Issue a warning about impossibility to convert to XSD any.
        pass

    xml_writer.add_attribute('namespace', val)


def _dump_schema(schema, xml_writer):
    with _TagGuard('schema', xml_writer):
        if schema.target_ns is not None:
            xml_writer.add_attribute('targetNamespace', schema.target_ns)
            xml_writer.define_namespace(None, schema.target_ns)

        imports = sorted(xml_writer.imports.get(schema, []),
                         key=lambda x: None if not x else x.target_ns)
        for sub_schema in imports:
            if sub_schema is None:
                continue

            assert sub_schema.prefix, 'No prefix for imported schema'
            xml_writer.define_namespace(sub_schema.prefix,
                                        sub_schema.target_ns)

        if imports:
            xml_writer.add_comment('Imports')
        for sub_schema in imports:
            with _TagGuard('import', xml_writer):
                if sub_schema is None:
                    xml_writer.add_attribute('namespace', base.XML_NAMESPACE)
                    xml_writer.add_attribute('schemaLocation', _XML_XSD_URI)
                    continue

                xml_writer.add_attribute('namespace', sub_schema.target_ns)
                xml_writer.add_attribute('schemaLocation',
                                         '{}.xsd'.format(sub_schema.filename))

        simple_types = xml_writer.stypes.get(schema, {})
        if simple_types:
            xml_writer.add_comment('Simple Types')
        for st in sorted(simple_types.itervalues(), key=lambda x: x.name):
            with _TagGuard('simpleType', xml_writer):
                xml_writer.add_attribute('name', st.name)

                if st.restriction is not None:
                    _dump_restriction(st.restriction, schema, xml_writer)
                elif st.listitems:
                    _dump_listitems(st.listitems, schema, xml_writer)
                elif st.union:
                    _dump_union(st.union, schema, xml_writer)

        complex_types = xml_writer.ctypes.get(schema, {})
        if complex_types:
            xml_writer.add_comment('Complex Types')
        for ct in sorted(complex_types.itervalues(), key=lambda x: x.name):
            with _TagGuard('complexType', xml_writer):
                xml_writer.add_attribute('name', ct.name)
                if ct.mixed:
                    xml_writer.add_attribute('mixed', str(ct.mixed).lower())

                if checks.has_simple_content(ct):
                    _dump_simple_content(ct, schema, xml_writer)
                elif ct.mixed or checks.has_complex_content(ct):
                    _dump_particle(ct, ct.structure, schema, xml_writer, set())

                    _dump_attribute_uses(ct, ct.attribute_uses(),
                                         schema, xml_writer)
                elif list(ct.attribute_uses()):
                    assert checks.has_empty_content(ct), 'Expected empty CT'
                    _dump_attribute_uses(ct, ct.attribute_uses(),
                                         schema, xml_writer)

        attr_groups = xml_writer.agroups.get(schema, {})
        if attr_groups:
            xml_writer.add_comment('Attribute Groups')
        for (name, attr_use) in sorted(attr_groups.itervalues(),
                                       key=lambda x: x.name):
            with _TagGuard('attributeGroup', xml_writer):
                xml_writer.add_attribute('name', name)

                _dump_attribute_use(attr_use, schema, xml_writer)

        elements = xml_writer.elements.get(schema, {})
        if elements:
            xml_writer.add_comment('Top-level Elements')
        for elem in sorted(elements.itervalues(), key=lambda x: x.name):
            with _TagGuard('element', xml_writer):
                _dump_element_attributes(elem, True, schema, xml_writer)

        elem_groups = xml_writer.egroups.get(schema, {})
        if elem_groups:
            xml_writer.add_comment('Element Groups')
        for (ct, name, particle) in sorted(elem_groups.itervalues(),
                                           key=lambda x: x.name):
            with _TagGuard('group', xml_writer):
                xml_writer.add_attribute('name', name)

                _dump_particle(ct, particle, schema, xml_writer,
                               set(), in_group=True)


def dump_xsd(schemata, output_dir, opacity_manager, horn):
    ctypes = {}
    stypes = {}
    elements = _select_top_elements(schemata, opacity_manager, ctypes, stypes)
    _select_complex_types(schemata, opacity_manager, ctypes, stypes)
    _simplify_simple_types(stypes, opacity_manager)
    agroups = _collect_attribute_groups(schemata, opacity_manager)
    egroups = _collect_element_groups(schemata, opacity_manager)
    imports = _collect_imports(ctypes, stypes, opacity_manager)

    horn.beep('Dumping XML Schema files to {}...',
              os.path.realpath(output_dir))

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    for schema in schemata:
        if (schema not in elements and schema not in ctypes and
                schema not in stypes and schema not in agroups and
                schema not in egroups):
            continue

        file_path = os.path.join(output_dir, '{}.xsd'.format(schema.filename))

        xml_writer = _XmlWritingContext(file_path, opacity_manager)
        xml_writer.elements = elements
        xml_writer.ctypes = ctypes
        xml_writer.stypes = stypes
        xml_writer.agroups = agroups
        xml_writer.egroups = egroups
        xml_writer.imports = imports

        _dump_schema(schema, xml_writer)

        xml_writer.done()


def _stypes_adder(stypes, t):
    schema_sts = stypes.setdefault(t.schema, {})
    schema_sts.setdefault(t.name, t)


def _ctypes_adder(ctypes, t):
    schema_cts = ctypes.setdefault(t.schema, {})
    schema_cts.setdefault(t.name, t)


def _do_for_single_valued_type(t, do_ctypes, do_stypes):
    # This function traverses single-valued types and invokes given
    # handlers for found types.
    if checks.is_single_valued_type(t):
        if checks.is_simple_type(t):
            do_stypes(t)

            if checks.is_restriction_type(t):
                base = t.restriction.base
                _do_for_single_valued_type(base, do_ctypes, do_stypes)
            elif checks.is_list_type(t):
                for i in t.listitems:
                    _do_for_single_valued_type(i.type, do_ctypes, do_stypes)
            elif checks.is_union_type(t):
                for u in t.union:
                    _do_for_single_valued_type(u, do_ctypes, do_stypes)
        elif checks.is_complex_type(t):
            do_ctypes(t)

            if checks.is_primitive_type(t):
                _do_for_single_valued_type(t, do_ctypes, do_stypes)
            elif checks.is_text_complex_type(t):
                _do_for_single_valued_type(t.text(), do_ctypes, do_stypes)
            elif checks.is_single_attribute_type(t):
                attr = next(t.attribute_uses()).attribute
                _do_for_single_valued_type(attr.type, do_ctypes, do_stypes)
        # If the type is native type then we don't need to process it.


def _select_top_elements(schemata, opacity_manager, ctypes, stypes):
    elements = {}
    for schema in schemata:
        if opacity_manager.is_opaque_ns(schema.target_ns):
            continue

        for e in schema.elements:
            if opacity_manager.is_opaque_top_element(e):
                continue

            _do_for_single_valued_type(
                e.type, functools.partial(_ctypes_adder, ctypes),
                functools.partial(_stypes_adder, stypes))

            schema_elems = elements.setdefault(schema, {})
            schema_elems[e.name] = e

    return elements


def _select_complex_types(schemata, opacity_manager, ctypes, stypes):
    for schema in schemata:
        if opacity_manager.is_opaque_ns(schema.target_ns):
            continue

        for ct in schema.complex_types:
            if opacity_manager.is_opaque_ct(ct):
                continue

            _ctypes_adder(ctypes, ct)

            for x in enums.enum_supported_flat(ct, opacity_manager):
                if checks.is_particle(x):
                    _do_for_single_valued_type(
                        x.term.type, functools.partial(_ctypes_adder, ctypes),
                        functools.partial(_stypes_adder, stypes))
                elif checks.is_attribute_use(x):
                    t = x.attribute.type
                    _do_for_single_valued_type(
                        t, functools.partial(_ctypes_adder, ctypes),
                        functools.partial(_stypes_adder, stypes))
                elif checks.is_text(x):
                    _do_for_single_valued_type(
                        x.type, functools.partial(_ctypes_adder, ctypes),
                        functools.partial(_stypes_adder, stypes))


def _simplify_simple_types(stypes, opacity_manager):
    # SimpleType simplification is necessary in some cases for RelaxNG schemas.
    for (schema, simple_types) in stypes.iteritems():
        for st in list(simple_types.itervalues()):
            if len(st.listitems) > 1:
                union_st = elements.SimpleType(st.name + '-union', st.schema)
                union_st.union = st.listitems

                min_occurs = 0
                max_occurs = 1
                for i in st.listitems:
                    if i.min_occurs > min_occurs:
                        min_occurs = i.min_occurs
                    elif i.max_occurs > max_occurs:
                        max_occurs = i.max_occurs
                new_st = elements.SimpleType(st.name, st.schema)
                new_st.listitems.append(
                    uses.ListTypeCardinality(union_st, min_occurs, max_occurs))

                assert new_st.name not in simple_types
                simple_types[new_st.name] = new_st

    return stypes


def _collect_attribute_groups(schemata, opacity_manager):
    # This function finds all attributes referenced from other schemata
    # and later these attributes are dumped as xsd:attributeGroup elements.
    agroups = {}

    AttributeGroup = collections.namedtuple('AttributeGroup',
                                            ['name', 'attr_use'])

    def find_groups(ct, attr_use, schema, group_count):
        # This function should do checks similar to those in
        # function _dump_attribute_use().
        attribute = attr_use.attribute

        if (opacity_manager.is_opaque_ct_member(ct, attribute) or
                checks.is_xml_attribute(attribute) or
                checks.is_any(attribute) or attribute.schema == schema):
            return group_count

        group_name = 'AttributeGroup{}'.format(group_count)
        groups = agroups.setdefault(attribute.schema, {})
        groups.setdefault(attribute, AttributeGroup(group_name, attr_use))
        return group_count + 1

    group_count = 1
    for schema in schemata:
        for ct in schema.complex_types:
            if opacity_manager.is_opaque_ct(ct):
                continue

            for u in ct.attribute_uses():
                group_count = find_groups(ct, u, schema, group_count)

    return agroups


def _collect_element_groups(schemata, opacity_manager):
    # This function finds all particles referenced from other schemata
    # and later these particles are dumped as xsd:group element.
    # In case we have anything opaque we assume that particle is equally
    # opaque across all its uses in different CTs and thus it doesn't
    # matter with which CT we add it resulting groups.
    egroups = {}

    ElementGroup = collections.namedtuple('ElementGroup',
                                          ['ct', 'name', 'particle'])

    def find_groups(ct, particle, schema, group_count):
        compositors = []

        # First check elements.
        for p in particle.term.members:
            if not checks.is_particle(p):
                continue
            elif checks.is_compositor(p.term):
                compositors.append(p)
                continue
            elif opacity_manager.is_opaque_ct_member(ct, p.term):
                continue
            elif checks.is_any(p.term):
                continue

            assert checks.is_element(p.term)

            if p.term.schema == schema:
                continue

            top_elements = [e for e in p.term.schema.elements]
            if p.term in top_elements:
                continue

            group_name = 'ElementGroup{}'.format(group_count)
            groups = egroups.setdefault(p.term.schema, {})
            groups.setdefault(particle.term,
                              ElementGroup(ct, group_name, particle))
            return group_count + 1

        # Then recurse into compositors.
        for c in compositors:
            group_count = find_groups(ct, c, schema, group_count)

        return group_count

    group_count = 1
    for schema in schemata:
        for ct in schema.complex_types:
            if opacity_manager.is_opaque_ct(ct):
                continue

            if ct.mixed or checks.has_complex_content(ct):
                group_count = find_groups(ct, ct.structure,
                                          schema, group_count)

    return egroups


def _collect_imports(ctypes, stypes, opacity_manager):
    imports = {}
    for (schema, complex_types) in list(ctypes.iteritems()):
        def imports_adder(t):
            if t.schema != schema:
                schema_imports = imports.setdefault(schema, set())
                schema_imports.add(t.schema)

        for ct in complex_types.itervalues():
            for x in enums.enum_supported_flat(ct, opacity_manager):
                if checks.is_particle(x):
                    _do_for_single_valued_type(
                        x.term.type, imports_adder, imports_adder)
                elif checks.is_attribute_use(x):
                    _do_for_single_valued_type(
                        x.attribute.type, imports_adder, imports_adder)
                elif checks.is_text(x):
                    _do_for_single_valued_type(
                        x.type, imports_adder, imports_adder)

    return imports
