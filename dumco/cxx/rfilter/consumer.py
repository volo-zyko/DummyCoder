# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.cxx.cpp_file import *


class ConsumerCoder(object):
    def __init__(self, gd, ct, context_class, context_class_header):
        self.gd = gd
        self.ct = ct
        self.context_class = context_class
        self.context_class_header = context_class_header
        self.namespaces = gd.nsc.uri_to_namespaces(self.ct.schema.target_ns)

    def generate_code(self):
        sf = CppHeaderFile(self.gd.lm.consumer_full_path(self.ct))
        with FileGuard(sf):
            sf.add_include('support/cxx/XmlDataConsumer.h', last=True)
            sf.add_include(self.context_class_header, last=True)

            with NsGuard(sf, self.namespaces):
                self._generate_class_decl(sf)

    def _generate_class_decl(self, sf):
        sf << 'class ' << self.gd.nm.consumer_class(self.ct)
        sf << ': public XMLSupport::XmlDataConsumer<'
        sf << self.context_class << '>' << nl
        sf << '{' << nl

        sf << 'public:' << nl_idt
        sf << self.gd.nm.consumer_class(self.ct)
        sf << '(' << self.context_class << '& context):' << nl_idt
        sf << 'XmlDataConsumer(context)' << nl_uidt
        sf << '{}' << nl_uidt

        sf << '};' << nl
