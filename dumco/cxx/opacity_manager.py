# Distributed under the GPLv2 License; see accompanying file COPYING.

import re

import dumco.schema.checks
import dumco.utils.string_utils


class OpacityManager(object):
    _LINE_MATCHER = re.compile('^(.*)\|(.*)\|(.*)$')
    _IGNORABLE = re.compile('(^#.*$)|(\s+#.*$)|(\s*)')

    def __init__(self, supported_elements_file):
        self.supported = {}

        self._load_list_file(supported_elements_file)

    def is_opaque(self, ct):
        try:
            return ct.name not in self.supported[ct.schema.target_ns]
        except KeyError:
            return not self._is_everything_supported()

    def is_opaque_member(self, ct, member):
        if dumco.schema.checks.is_any(member):
            return True
        elif self._is_everything_supported():
            return False

        try:
            member_set = self.supported[ct.schema.target_ns][ct.name]
        except KeyError:
            return True

        if dumco.schema.checks.is_element(member):
            name = dumco.utils.string_utils.cxx_name(ct, member)
        elif dumco.schema.checks.is_attribute(member):
            name = '@{}'.format(dumco.utils.string_utils.cxx_name(ct, member))
        elif dumco.schema.checks.is_text(member):
            name = 'text()'
        else: # pragma: no cover
            assert False
        return (name not in member_set)

    def _is_everything_supported(self):
        return len(self.supported) == 0

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

                member_name = m.group(3)

                if member_name.startswith('#'):
                    continue

                uri = m.group(1)
                ct_name = m.group(2)

                ns_map = self.supported.setdefault(uri, dict())
                member_set = ns_map.setdefault(ct_name, set())
                member_set.add(member_name)
