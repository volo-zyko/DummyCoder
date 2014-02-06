# Distributed under the GPLv2 License; see accompanying file COPYING.

import itertools
import re
import string


class NamespaceConverter(object):
    _PATHSEP_MATCHER = re.compile('[/:]')
    _ALLOWED_DIGITS = set(string.digits)
    _ALLOWED_FIRST_CHARS = set(string.ascii_letters + '_')
    _ALLOWED_CHARS = set(_ALLOWED_DIGITS).union(_ALLOWED_FIRST_CHARS)

    def __init__(self, common_namespaces, uri_to_ns_map, uri_bases):
        self.common_namespaces = common_namespaces
        self.uri_bases = uri_bases

        self.ns_mapping = self._parse_mapping(uri_to_ns_map)

    def uri_to_namespaces(self, uri):
        if not hasattr(self.ns_mapping, uri):
            self.ns_mapping[uri] = self._find_ns_for_uri(uri)

        return self.ns_mapping[uri]

    def _parse_mapping(self, uri_to_ns_map):
        result = {}
        for uri in ([] if uri_to_ns_map is None else uri_to_ns_map):
            key = uri[:uri.index('!')]
            value = uri[uri.index('!') + 1:]

            result[key] = self.common_namespaces + \
                map(lambda n: self._normalize(n), value.split(','))
        return result

    def _find_ns_for_uri(self, uri):
        for base in ([] if self.uri_bases is None else self.uri_bases):
            if not uri.startswith(base):
                continue

            result = self.common_namespaces + \
                filter(lambda n: n is not None,
                       map(lambda n: self._normalize(n),
                           self._PATHSEP_MATCHER.split(uri[len(base):])))
            return result

        assert hasattr(self.ns_mapping, uri), \
            'There is no namespace mapping for uri {}'.format(uri)

    @staticmethod
    def _normalize(name):
        result = list(itertools.dropwhile(
            lambda c: c == '_' or c in NamespaceConverter._ALLOWED_DIGITS,
            map(lambda c: c if c in NamespaceConverter._ALLOWED_CHARS else '_',
                list(name))))
        return (None if result == []
                else ''.join([result[0].upper()] + result[1:]))
