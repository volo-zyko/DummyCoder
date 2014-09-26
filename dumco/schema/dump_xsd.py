# Distributed under the GPLv2 License; see accompanying file COPYING.

import collections
import functools
import os.path
import shutil
import StringIO

import base
import checks
import elements
import enums
import uses
import xsd_types

from prv.dump_utils import XSD_PREFIX, TagGuard, XmlWriter, \
    dump_restriction, dump_listitems, dump_union, dump_simple_content, \
    dump_particle, dump_attribute_uses, dump_attribute_use, \
    dump_element_attributes


class _FakeSchemaTagGuard(object):
    def __init__(self, context):
        self.context = context
        self.old_fhandle = context.fhandle
        context.fhandle = context.buffered_fhandle

    def __enter__(self):
        assert self.context.indentation == 0
        assert len(self.context.namespaces) == 0

        self.context.namespaces[XSD_PREFIX] = xsd_types.XSD_NAMESPACE
        self.context.indentation = 1
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        assert self.context.indentation == 1

        self.context.namespaces = {}
        self.context.indentation = 0
        self.context.fhandle = self.old_fhandle
        return exc_value is None


class _SchemaDumpContext(XmlWriter):
    def __init__(self, filename, opacity_manager, elements,
                 ctypes, stypes, agroups, egroups, schemata):
        self.om = opacity_manager

        # We track here elements, complex types, simple types, attribute groups
        # and element groups. In this case _SchemaDumpContext is used as global
        # object.
        self.elements = elements
        self.ctypes = ctypes
        self.stypes = stypes
        self.agroups = agroups
        self.egroups = egroups
        self.schemata = schemata

        self.imported_namespaces = {}

        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        self.fhandle = open(filename, 'w')
        # We use this buffer for writing schema content allowing to postpone
        # writing it to file till we know all imports.
        self.buffered_fhandle = StringIO.StringIO()

        # Init parent class after self-initialization since parent will
        # immediately write XML header
        super(_SchemaDumpContext, self).__init__()

    def _write(self, text):
        self.fhandle.write(text)

    def _close(self):
        assert hasattr(self.fhandle, 'name')
        self.fhandle.flush()
        self.fhandle.close()

    def _dump_schema_content(self, schema):
        simple_types = self.stypes.get(schema, {})
        if simple_types:
            self.add_comment('Simple Types')
        for st in sorted(simple_types.itervalues(), key=lambda x: x.name):
            with TagGuard('simpleType', self):
                self.add_attribute('name', st.name)

                if st.restriction is not None:
                    dump_restriction(st.restriction, schema, self)
                elif st.listitems:
                    dump_listitems(st.listitems, schema, self)
                elif st.union:
                    dump_union(st.union, schema, self)

        complex_types = self.ctypes.get(schema, {})
        if complex_types:
            self.add_comment('Complex Types')
        for ct in sorted(complex_types.itervalues(), key=lambda x: x.name):
            with TagGuard('complexType', self):
                self.add_attribute('name', ct.name)
                if ct.mixed:
                    self.add_attribute('mixed', str(ct.mixed).lower())

                if checks.has_simple_content(ct):
                    dump_simple_content(ct, schema, self)
                elif ct.mixed or checks.has_complex_content(ct):
                    dump_particle(ct, ct.structure, schema, self, set())

                    dump_attribute_uses(ct, ct.attribute_uses(), schema, self)
                elif list(ct.attribute_uses()):
                    assert checks.has_empty_content(ct), 'Expected empty CT'
                    dump_attribute_uses(ct, ct.attribute_uses(), schema, self)

        attr_groups = self.agroups.get(schema, {})
        if attr_groups:
            self.add_comment('Attribute Groups')
        for (name, attr_use) in sorted(attr_groups.itervalues(),
                                       key=lambda x: x.name):
            with TagGuard('attributeGroup', self):
                self.add_attribute('name', name)

                dump_attribute_use(attr_use, schema, self)

        elements = self.elements.get(schema, {})
        if elements:
            self.add_comment('Top-level Elements')
        for elem in sorted(elements.itervalues(), key=lambda x: x.name):
            with TagGuard('element', self):
                dump_element_attributes(elem, True, schema, self)

        in_group = True
        elem_groups = self.egroups.get(schema, {})
        if elem_groups:
            self.add_comment('Element Groups')
        for (ct, name, particle) in sorted(elem_groups.itervalues(),
                                           key=lambda x: x.name):
            with TagGuard('group', self):
                self.add_attribute('name', name)

                dump_particle(ct, particle, schema, self, set(), in_group)

    def define_namespace(self, prefix, uri):
        if self.fhandle == self.buffered_fhandle:
            # We are writing to buffer so for now we don't define namespaces.
            # I.e. make the parent behave as if the namespaces were
            # already defined.
            self.namespaces[prefix] = uri

        super(_SchemaDumpContext, self).define_namespace(prefix, uri)

    def store_import_namespace(self, prefix, uri):
        assert (prefix not in self.imported_namespaces or
                self.imported_namespaces[prefix] == uri)
        self.imported_namespaces[prefix] = uri

    def dump_schema(self, schema):
        with _FakeSchemaTagGuard(self):
            self._dump_schema_content(schema)

            # Now all required namepaces are defined.
            import_namespaces = self.imported_namespaces

        with TagGuard('schema', self):
            if schema.target_ns is not None:
                self.add_attribute('targetNamespace', schema.target_ns)
                self.define_namespace(None, schema.target_ns)

            sorted_namespaces = sorted(import_namespaces.iteritems())
            for (prefix, uri) in sorted_namespaces:
                if uri == base.XML_NAMESPACE or uri == schema.target_ns:
                    continue

                assert prefix, 'No prefix for imported schema'
                self.define_namespace(prefix, uri)

            if sorted_namespaces:
                self.add_comment('Imports')
            for (prefix, uri) in sorted_namespaces:
                sub_schema = next((s for s in self.schemata
                                   if s.target_ns == uri), None)

                with TagGuard('import', self):
                    if uri == schema.target_ns:
                        continue

                    if uri == base.XML_NAMESPACE:
                        self.add_attribute('namespace', base.XML_NAMESPACE)
                        self.add_attribute('schemaLocation',
                                           xsd_types.XML_XSD_URI)
                        continue

                    assert sub_schema is not None
                    self.add_attribute('namespace', uri)
                    self.add_attribute('schemaLocation',
                                       '{}.xsd'.format(sub_schema.filename))

            # Now when namespaces and imports are written we write
            # the rest of schema content.
            self.add_wellformed_xml(self.buffered_fhandle.getvalue())
            self.buffered_fhandle.close()

        self.done()


def _stypes_adder(stypes, t):
    schema_sts = stypes.setdefault(t.schema, {})
    schema_sts.setdefault(t.name, t)


def _ctypes_adder(ctypes, t):
    schema_cts = ctypes.setdefault(t.schema, {})
    schema_cts.setdefault(t.name, t)


def _do_for_single_valued_type(t, do_ctypes, do_stypes):
    # This function traverses single-valued types and invokes given
    # handlers for found types.
    if not checks.is_single_valued_type(t):
        return

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

        if checks.is_text_complex_type(t):
            _do_for_single_valued_type(t.text().type, do_ctypes, do_stypes)
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


def _approximate_simple_types(stypes, opacity_manager):
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
    # matter with which CT we add it to resulting groups.
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
            elif p.term.schema == schema:
                continue
            elif p.term in [e for e in p.term.schema.elements]:
                continue

            assert checks.is_element(p.term)

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


def dump_xsd(schemata, output_dir, opacity_manager, horn):
    ctypes = {}
    stypes = {}
    elements = _select_top_elements(schemata, opacity_manager, ctypes, stypes)
    _select_complex_types(schemata, opacity_manager, ctypes, stypes)
    _approximate_simple_types(stypes, opacity_manager)
    agroups = _collect_attribute_groups(schemata, opacity_manager)
    egroups = _collect_element_groups(schemata, opacity_manager)

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

        dumper = _SchemaDumpContext(file_path, opacity_manager, elements,
                                    ctypes, stypes, agroups, egroups, schemata)

        dumper.dump_schema(schema)
