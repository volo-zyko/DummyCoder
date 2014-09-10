# Distributed under the GPLv2 License; see accompanying file COPYING.

import os

import cpp_file


class GenerationDriver(object):
    def __init__(self, schemata, ns_converter, opacity_manager):
        self.schemata = schemata
        self.nsc = ns_converter
        self.om = opacity_manager

    def generate(self):
        for (schema_file, schema) in self.schemata.iteritems():
            for ct in schema.complex_types.itervalues():
                if not self.om.is_opaque_ct(ct):
                    self._generate_for_complex_type(ct)
