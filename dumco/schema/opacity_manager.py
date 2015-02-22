# Distributed under the GPLv2 License; see accompanying file COPYING.

import operator
import re

import dumco.schema.checks as checks
import dumco.schema.enums as enums
import dumco.schema.model as model
import dumco.schema.tuples as tuples
import dumco.schema.uses as uses
from dumco.utils.horn import horn
from dumco.utils.string_utils import cxx_name


class OpacityManager(object):
    _LINE_MATCHER = re.compile('^([^|]*)\|([^|]*)(\|(.*))?$')
    _IGNORABLE = re.compile('(^#.*$)|(\s+#.*$)|(\s*)')

    def __init__(self, supported_elements_file):
        self.supported_cts = {}
        self.supported_elems = {}

        self._load_list_file(supported_elements_file)

    def is_opaque_anything(self):
        return len(self.supported_cts) != 0 or len(self.supported_elems) != 0

    def is_opaque_ns(self, ns):
        return (self.is_opaque_anything() and
                not ns in self.supported_cts and
                not ns in self.supported_elems)

    def is_opaque_top_element(self, elem):
        return (self.is_opaque_anything() and
                (elem.name not in
                 self.supported_elems.get(elem.schema.target_ns, set())))

    def is_opaque_ct(self, ct):
        return (self.is_opaque_anything() and
                (ct.name not in
                 self.supported_cts.get(ct.schema.target_ns, set())))

    def is_opaque_ct_member(self, ct, member, is_attr=False):
        return (self.is_opaque_anything() and
                _get_member_predicate(member, ct.schema, is_attr) not in
                self.supported_cts.get(ct.schema.target_ns, {}).get(ct.name,
                                                                    set()))

    def ensure_consistency(self, schemata):
        if not self.is_opaque_anything():
            return True

        def check_schema_consistency(ct):
            def cumulative_min_occurs(parents, particle):
                min_occurs = 1
                for p in parents + [particle]:
                    if checks.is_complex_type(p):
                        continue

                    min_occurs = uses.min_occurs_op(
                        min_occurs, p.min_occurs, operator.mul)

                return min_occurs

            status = True
            for (ps, x) in enums.enum_hierarchy(ct):
                if checks.is_particle(x):
                    if (cumulative_min_occurs(ps, x) > 0 and
                            self.is_opaque_ct_member(ct, x.term)):
                        horn.honk('Element {} in {}:{} is required but is '
                                  'opaque, you may want to add the following '
                                  'to supported list\n{}|{}|{}\n', x.term.name,
                                  ct.schema.target_ns, ct.name,
                                  ct.schema.target_ns, ct.name,
                                  cxx_name(x.term, ct.schema))
                        status = False
                    elif (not self.is_opaque_ct_member(ct, x.term) and
                            checks.is_complex_type(x.term.type) and
                            self.is_opaque_ct(x.term.type) and
                            not checks.is_single_valued_type(x.term.type)):
                        horn.honk('ComplexType {}:{} which is referenced '
                                  'from {}:{}#{} is opaque\n',
                                  x.term.type.schema.target_ns,
                                  x.term.type.name, ct.schema.target_ns,
                                  ct.name, cxx_name(x.term, ct.schema))
                        status = False
                elif (checks.is_attribute_use(x) and x.required and
                        self.is_opaque_ct_member(ct, x.attribute, True)):
                    horn.honk('Attribute {} in {}:{} is required but is '
                              'opaque, you may want to add the following to '
                              'supported list\n{}|{}|@{}\n', x.attribute.name,
                              ct.schema.target_ns, ct.name,
                              ct.schema.target_ns, ct.name,
                              cxx_name(x.attribute, ct.schema))
                    status = False
                elif (checks.is_text(x) and
                        self.is_opaque_ct_member(ct, x) and
                        checks.has_simple_content(ct) and
                        checks.is_primitive_type(x.type)):
                    horn.honk('Text content in non-opaque ComplexType '
                              '{}:{} with simple content is opaque\n',
                              ct.schema.target_ns, ct.name)
                    status = False

            return status

        consistent = True
        schemata_cts = {}
        schemata_elements = {}
        occurences = {}

        # Check whether schema constraints (required elements/attributes/
        # complex types, etc) are obeyed by supported list.
        for schema in schemata:
            if self.is_opaque_ns(schema.target_ns):
                continue

            element_set = schemata_elements.setdefault(schema.target_ns, set())
            for elem in schema.elements:
                element_set.add(elem.name)

                if (self.is_opaque_top_element(elem) or
                        checks.is_single_valued_type(elem.type)):
                    continue

                if self.is_opaque_ct(elem.type):
                    horn.honk('ComplexType {}:{} is required by top-level '
                              'element {}:{} but is opaque\n',
                              elem.type.schema.target_ns, elem.type.name,
                              elem.schema.target_ns, elem.name)
                    consistent = False

            ct_map = schemata_cts.setdefault(schema.target_ns, {})
            for ct in schema.complex_types:
                if checks.is_single_valued_type(ct):
                    continue

                can_ignore = self.is_opaque_ct(ct)
                member_set = ct_map.setdefault(ct.name, set())
                for m in enums.enum_flat(ct):
                    if checks.is_particle(m):
                        if not can_ignore and checks.is_element(m.term):
                            cts = occurences.setdefault(
                                tuples.HashableParticle(m, None), [])
                            cts.append(ct)
                        member_set.add(
                            _get_member_predicate(m.term, ct.schema, False))
                    elif checks.is_attribute_use(m):
                        if not can_ignore and checks.is_attribute(m.attribute):
                            cts = occurences.setdefault(
                                tuples.HashableAttributeUse(m, None), [])
                            cts.append(ct)
                        member_set.add(
                            _get_member_predicate(m.attribute, ct.schema, True))
                    elif checks.is_text(m):
                        member_set.add(
                            _get_member_predicate(m, ct.schema, False))

                if can_ignore:
                    continue

                consistent = check_schema_consistency(ct) and consistent

        # Check whether same elements/attributes (probably originally
        # referenced through group/attributeGroup) are fully supported or fully
        # unsupported across all complex types from which they were referenced.
        for (m, cts) in occurences.iteritems():
            if len(cts) == 1:
                continue

            member = m.component
            if checks.is_particle(member):
                support_in_ct = [
                    (self.is_opaque_ct_member(ct, member.term), ct)
                    for ct in cts]
                if not all([p[0] == support_in_ct[0][0]
                            for p in support_in_ct]):
                    horn.howl('Probably the same element \'{}\' is supported '
                              'in {} and is non-supported in {}\n',
                              member.term.name,
                              str([str(ct.name) for (s, ct)
                                   in support_in_ct if s]),
                              str([str(ct.name) for (s, ct)
                                   in support_in_ct if not s]))
            elif checks.is_attribute_use(member):
                support_in_ct = [
                    (self.is_opaque_ct_member(ct, member.attribute), ct)
                    for ct in cts]
                if not all([p[0] == support_in_ct[0][0]
                            for p in support_in_ct]):
                    horn.howl('Probably the same attribute \'{}\' is supported '
                              'in {} and is non-supported in {}\n',
                              member.attribute.name,
                              str([str(ct.name) for (s, ct)
                                   in support_in_ct if s]),
                              str([str(ct.name) for (s, ct)
                                   in support_in_ct if not s]))

        # Check whether top-level elements mentioned as supported are present
        # in schemata.
        for (target_ns, list_file_elems) in self.supported_elems.iteritems():
            schema_elems = schemata_elements.get(target_ns, set())

            for member in list_file_elems:
                if not member in schema_elems:
                    horn.honk('Top-level element {}|{} is marked as supported '
                              'but does not correspond to anything in schema '
                              'files\n', target_ns, member)
                    consistent = False

        # Check whether complex types and their content mentioned as supported
        # are present in schemata.
        for (target_ns, list_file_cts) in self.supported_cts.iteritems():
            schema_cts = schemata_cts.get(target_ns, {})

            for (ct_name, member_set) in list_file_cts.iteritems():
                if not ct_name in schema_cts:
                    horn.honk('Complex type {}|{} is marked as supported but '
                              'does not correspond to anything in schema '
                              'files or is primitive type by its nature\n',
                              target_ns, ct_name)
                    consistent = False

                schema_members = schema_cts.get(ct_name, set())

                for member in member_set:
                    if not member in schema_members:
                        horn.honk('Schema component {}|{}|{} is marked as '
                                  'supported but does not correspond to '
                                  'anything in schema files\n', target_ns,
                                  ct_name, member)
                        consistent = False

        return consistent

    def _load_list_file(self, supported_elements_file):
        if supported_elements_file is None:
            return

        with open(supported_elements_file, 'r') as fl:
            for line in fl.readlines():
                cleaned_line = OpacityManager._IGNORABLE.sub('', line)
                if cleaned_line == '':
                    continue

                m = OpacityManager._LINE_MATCHER.match(cleaned_line)
                assert m is not None, ''

                member_name = m.group(4)

                if member_name is None:
                    uri = m.group(1)
                    element_name = m.group(2)

                    element_set = self.supported_elems.setdefault(uri, set())
                    element_set.add(element_name)
                    continue
                elif member_name.startswith('#'):
                    continue

                uri = m.group(1)
                ct_name = m.group(2)

                ns_map = self.supported_cts.setdefault(uri, dict())
                member_set = ns_map.setdefault(ct_name, set())
                member_set.add(member_name)


def _get_member_predicate(member, other_schema, is_attr):
    if checks.is_element(member):
        return cxx_name(member, other_schema)
    elif checks.is_attribute(member):
        return '@' + cxx_name(member, other_schema)
    elif checks.is_text(member):
        return 'text()'
    elif checks.is_any(member):
        def constraint_str(c):
            if isinstance(c, model.Any.Name):
                if c.tag is not None:
                    return 'tag={}'.format(c.tag)
                elif c.ns is not None:
                    return 'ns={}'.format(c.ns)
            elif isinstance(c, model.Any.Not):
                return '!{}'.format(constraint_str(c.name))

        if member.constraint is None:
            return '*'
        else:
            return '{}*[{}]'.format('@' if is_attr else '',
                                    constraint_str(member.constraint))

    assert False
