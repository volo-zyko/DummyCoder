# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.cxx.cpp_file import *


class StateHeaderCoder(object):
    def __init__(self, gd, ct):
        self.gd = gd
        self.ct = ct
        self.ct_namespaces = gd.nsc.uri_to_namespaces(ct.schema.target_ns)

    def generate_code(self):
        sf = CppHeaderFile(self.gd.lm.state_header_path(self.ct))
        with FileGuard(sf):
            sf.add_include('support/cxx/XmlParsingState.h', last=True)

            with NsGuard(sf, self.ct_namespaces):
                self._generate_class_decl(sf)

    def _generate_class_decl(self, sf):
        sf << 'class ' << self.gd.nm.state_class(self.ct)
        sf << ': public XMLSupport::XmlParsingHandler' << nl
        sf << '{' << nl

        sf << '};' << nl
