# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.cxx.cpp_file import *
import dumco.schema.checks
import dumco.schema.enums
from dumco.utils.string_utils import *


class ConsumerCoder(object):
    def __init__(self, gd, ct, context_class, context_class_header):
        self.gd = gd
        self.ct = ct
        self.context_class = context_class
        self.context_class_header = context_class_header
        self.ct_namespaces = gd.nsc.uri_to_namespaces(ct.schema.target_ns)

    def generate_code(self):
        sf = CppHeaderFile(self.gd.lm.consumer_header_path(self.ct))
        with FileGuard(sf):
            sf.add_include('support/cxx/XmlDataConsumer.h', last=True)
            sf.add_include(self.context_class_header, last=True)

            with NsGuard(sf, self.ct_namespaces):
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
        sf << '{}'

        vsf = ValidatingSourceWrapper(sf)
        vsf << nl2_uidt << 'public: // text' << idt
        if self.ct.mixed:
            if not self.gd.om.is_opaque_member(self.ct, self.ct.text):
                vsf << valid << nl
                vsf << 'void AddTextContent(const std::string& text);'

        vsf = ValidatingSourceWrapper(sf)
        vsf << nl2_uidt << 'public: // attributes' << idt
        for (_, a) in dumco.schema.enums.enum_attribute_uses(self.ct):
            if not self.gd.om.is_opaque_member(self.ct, a.attribute):
                vsf << valid << nl
                self._generate_attribute_handler(vsf, a)

        vsf = ValidatingSourceWrapper(sf)
        vsf << nl2_uidt << 'public: // elements' << idt
        for (_, p) in dumco.schema.enums.enum_ct_particles(self.ct):
            if not self.gd.om.is_opaque_member(self.ct, p.term):
                vsf << valid << nl
                self._generate_element_handler(vsf, p)

        sf << nl_uidt << '};' << nl

    def _generate_element_handler(self, sf, part):
        sf << 'virtual '
        if (dumco.schema.checks.is_primitive_type(part.term.type) or
            dumco.schema.checks.is_text_complex_type(part.term.type)):
            sf << 'void ' << self.gd.nm.set_leaf(self.ct, part.term) << '('
        elif dumco.schema.checks.is_attributed_complex_type(part.term.type):
            sf << 'void ' << self.gd.nm.set_leaf(self.ct, part.term) << '('
        elif dumco.schema.checks.is_empty_complex_type(part.term.type):
            sf << 'void ' << self.gd.nm.set_present(self.ct, part.term) << '('
        else:
            sf << 'std::unique_ptr<' << self.gd.nm.consumer_class_ns(
                part.term.type, self.ct_namespaces) << '> '
            sf << self.gd.nm.get_consumer(self.ct, part.term) << '('
        sf << ') = 0;'

    def _generate_attribute_handler(self, sf, attr_use):
        sf << 'virtual void ' << self.gd.nm.set_attribute(
            self.ct, attr_use.attribute) << '('
        sf << ');'
