# Distributed under the GPLv2 License; see accompanying file COPYING.

import re

import dumco.schema.checks
import dumco.schema.enums
from dumco.utils.horn import horn
import dumco.utils.string_utils


class OpacityManager(object):
    _LINE_MATCHER = re.compile('^([^|]*)\|([^|]*)(\|(.*))?$')
    _IGNORABLE = re.compile('(^#.*$)|(\s+#.*$)|(\s*)')

    def __init__(self, supported_elements_file):
        self.supported_cts = {}
        self.toplevel_elems = {}

        self._load_list_file(supported_elements_file)

    def is_opaque_anything(self):
        return len(self.supported_cts) != 0 or len(self.toplevel_elems) != 0

    def is_opaque_ns(self, ns):
        return (not ns in self.supported_cts and
                not ns in self.toplevel_elems and
                self.is_opaque_anything())

    def is_opaque_top_element(self, elem):
        try:
            return elem.name not in self.toplevel_elems[elem.schema.target_ns]
        except KeyError:
            return self.is_opaque_anything()

    def is_opaque_ct(self, ct):
        try:
            return ct.name not in self.supported_cts[ct.schema.target_ns]
        except KeyError:
            return self.is_opaque_anything()

    def is_opaque_ct_member(self, ct, member):
        if not self.is_opaque_anything():
            return False
        elif dumco.schema.checks.is_any(member):
            return True

        try:
            member_set = self.supported_cts[ct.schema.target_ns][ct.name]
        except KeyError:
            return True

        if dumco.schema.checks.is_element(member):
            name = dumco.utils.string_utils.cxx_name(ct, member)
        elif dumco.schema.checks.is_attribute(member):
            name = '@{}'.format(dumco.utils.string_utils.cxx_name(ct, member))
        elif dumco.schema.checks.is_text(member):
            name = 'text()'
        else:  # pragma: no cover
            assert False
        return (name not in member_set)

    def ensure_consistency(self, schemata):
        if not self.is_opaque_anything():
            return True

        def cumulative_min_occurs(parents, particle):
            min_occurs = 1
            for p in parents[0:-1]:
                assert checks.is_compositor(p.term)

                min_occurs = min_occurs * p.min_occurs

            return min_occurs * particle.min_occurs

        consistent = True
        checks = dumco.schema.checks
        enums = dumco.schema.enums
        for schema in schemata:
            if self.is_opaque_ns(schema.target_ns):
                continue

            for elem in schema.elements:
                if (self.is_opaque_top_element(elem) or
                        checks.is_primitive_type(elem.type) or
                        checks.is_empty_complex_type(elem.type)):
                    continue

                if self.is_opaque_ct(elem.type):
                    horn.honk('ComplexType {}:{} is required by {}:{} '
                              'but is opaque', elem.type.schema.target_ns,
                              elem.type.name, elem.schema.target_ns, elem.name)
                    consistent = False

            for ct in schema.complex_types:
                if (self.is_opaque_ct(ct) or
                        checks.is_empty_complex_type(ct)):
                    continue

                for (p, x) in enums.enum_hierarchy(ct):
                    if (checks.is_particle(x) and
                            checks.is_compositor(x.term)):
                        continue

                    if (checks.is_particle(x) and checks.is_element(x.term) and
                            cumulative_min_occurs(p, x) > 0 and
                            self.is_opaque_ct_member(ct, x.term)):
                        horn.honk('Element {} in {}:{} is required but is '
                                  'opaque', x.term.name, ct.schema.target_ns,
                                  ct.name)
                        consistent = False
                    elif (checks.is_particle(x) and
                            checks.is_element(x.term) and
                            not self.is_opaque_ct_member(ct, x.term) and
                            not checks.is_single_valued_type(x.term.type) and
                            self.is_opaque_ct(x.term.type)):
                        horn.honk('ComplexType {}:{} which is referenced '
                                  'from {}:{}#{} is opaque',
                                  x.term.type.schema.target_ns,
                                  x.term.type.name, x.term.schema.target_ns,
                                  ct.name, x.term.name)
                        consistent = False
                    elif (checks.is_attribute_use(x) and x.required and
                            self.is_opaque_ct_member(ct, x.attribute)):
                        horn.honk('Attribute {} in {}:{} is required but is '
                                  'opaque', x.attribute.name,
                                  ct.schema.target_ns, ct.name)
                        consistent = False
                    elif (checks.is_text(x) and
                            self.is_opaque_ct_member(ct, x) and
                            checks.has_simple_content(ct) and
                            checks.is_simple_type(x.type)):
                        horn.honk('Text content in non-opaque ComplexType '
                                  '{}:{} with simple content is opaque',
                                  ct.schema.target_ns, ct.name)
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
                    elem_name = m.group(2)

                    elem_set = self.toplevel_elems.setdefault(uri, set())
                    elem_set.add(elem_name)
                    continue
                elif member_name.startswith('#'):
                    continue

                uri = m.group(1)
                ct_name = m.group(2)

                ns_map = self.supported_cts.setdefault(uri, dict())
                member_set = ns_map.setdefault(ct_name, set())
                member_set.add(member_name)
