# Distributed under the GPLv2 License; see accompanying file COPYING.

import itertools
import os.path
import StringIO

import dumco.schema.base
import dumco.schema.checks
import dumco.schema.elements
from dumco.schema.rng_types import RNG_NAMESPACE, rng_builtin_types
from dumco.schema.xsd_types import xsd_builtin_types

import prv.rng_choice
import prv.rng_define
import prv.rng_empty
import prv.rng_interleave
import prv.rng_grammar
import prv.rng_oneOrMore
import prv.rng_start
import prv.rng_text
import prv.rng_to_model


class RelaxElementFactory(object):
    def __init__(self, arguments, element_namer, extension):
        # Reset internals of this factory.
        self.reset()

        # These internals should not be reset.
        self.included_schema_paths = {}

        # All prefixes encountered during schemata loading.
        self.all_namespace_prefixes = {dumco.schema.base.XML_NAMESPACE: 'xml'}

        # Part of the factorie's interface.
        self.arguments = arguments
        self.namer = element_namer
        self.extension = extension

    def reset(self):
        # Internals of this factory.
        self.dispatcher_stack = []
        self.dispatcher = {
            'grammar': prv.rng_grammar.rng_grammar,
        }
        self.element_stack = []
        self.element = None
        self.datatypes_stack = []
        self.ns_attribute_stack = []
        self.namespaces = {'xml': dumco.schema.base.XML_NAMESPACE}
        self.parents = []

    def define_namespace(self, prefix, uri):
        if uri is None:
            # Remove namespace.
            assert prefix in self.namespaces, 'Closing non-existent namespace'
            del self.namespaces[prefix]
        else:
            # Add namespace.
            self.namespaces[prefix] = uri

            if prefix is not None and uri != RNG_NAMESPACE:
                # This makes sure that prefix will be the same no matter
                # what was the order of loading of schemata.
                if prefix > self.all_namespace_prefixes.get(uri, ''):
                    self.all_namespace_prefixes[uri] = prefix

    def new_element(self, name, attrs, schema_path, all_grammars):
        self.element_stack.append(self.element)

        # Here we don't support anything non-RelaxNG.
        if name[0] != RNG_NAMESPACE:
            self.element = None
            return

        self.dispatcher_stack.append(self.dispatcher)

        try:
            self.datatypes_stack.append(
                self.get_attribute(attrs, 'datatypeLibrary'))
        except LookupError:
            self.datatypes_stack.append(None)

        try:
            self.ns_attribute_stack.append(self.get_attribute(attrs, 'ns'))

            # If namespace is present but there is no prefix for
            # it then we create a new prefix.
            new_ns = self.ns_attribute_stack[-1]
            if new_ns not in self.all_namespace_prefixes:
                for x in xrange(0, dumco.schema.base.UNBOUNDED):
                    prefix = 'ns{}'.format(x)
                    if prefix not in self.namespaces:
                        self.all_namespace_prefixes[new_ns] = prefix
                        break
        except LookupError:
            self.ns_attribute_stack.append(None)

        assert self.dispatcher is None or name[1] in self.dispatcher, \
            '"{}" is not supported in {}'.format(
                name[1], self.element.__class__.__name__)

        if self.dispatcher is not None:
            (self.element, self.dispatcher) = self.dispatcher[name[1]](
                attrs, self.element, self, schema_path, all_grammars)

    def finalize_current_element(self, name):
        old_element = self.element
        self.element = self.element_stack.pop()

        # Here we don't support anything non-RelaxNG.
        if name[0] != RNG_NAMESPACE:
            return

        if old_element is not None:
            old_element.end_element(self)
        self.dispatcher = self.dispatcher_stack.pop()
        self.datatypes_stack.pop()
        self.ns_attribute_stack.pop()

    def end_document(self):
        # There might remain single xml namespace.
        assert len(self.namespaces) == 1 or len(self.namespaces) == 0
        assert len(self.dispatcher_stack) == 0
        assert len(self.element_stack) == 0

    def current_element_append_text(self, text):
        if self.element is not None:
            self.element.append_text(text)

    def finalize_documents(self, all_grammars):
        all_schemata = {}
        namespace_prefixes = {'': ''}
        if len(self.all_namespace_prefixes) > 1:
            namespace_prefixes = self.all_namespace_prefixes
        for (uri, prefix) in namespace_prefixes.iteritems():
            if dumco.schema.checks.is_xml_namespace(uri):
                continue

            schema = dumco.schema.elements.Schema(uri)
            schema.set_prefix(self.all_namespace_prefixes)
            schema.filename = 'ns' if schema.prefix is None else schema.prefix

            all_schemata[schema.target_ns] = schema

        sorted_all_grammars = sorted(all_grammars.values(),
                                     key=lambda g: g.grammar_path)

        converter = prv.rng_to_model.Rng2Model(all_schemata, self)
        for grammar in sorted_all_grammars:
            grammar.finalize(grammar, self)

            converter.convert(grammar)

        if self.arguments.dump_rng_model_to_dir is not None:
            # We don't really need to dump rng but this is an additional check
            # for validity of loaded grammars.
            if not os.path.exists(self.arguments.dump_rng_model_to_dir):
                os.makedirs(self.arguments.dump_rng_model_to_dir)
            for (c, grammar) in enumerate(all_grammars.itervalues(), start=1):
                stream = StringIO.StringIO()
                stream.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                grammar.dump(stream, 0)

                path = os.path.join(self.arguments.dump_rng_model_to_dir,
                                    os.path.basename(grammar.grammar_path))
                with open(path, 'w') as f:
                    f.write(stream.getvalue())

        sorted_all_schemata = filter(lambda s: not _is_schema_empty(s),
                                     all_schemata.itervalues())
        sorted_all_schemata.sort(key=lambda s: s.target_ns)
        return sorted_all_schemata

    def get_datatypes_uri(self):
        found = itertools.dropwhile(lambda x: x is None,
                                    reversed(self.datatypes_stack))
        return next(found, '')

    def get_ns(self):
        found = itertools.dropwhile(lambda x: x is None,
                                    reversed(self.ns_attribute_stack))
        return next(found, '')

    def builtin_types(self, uri):
        if dumco.schema.checks.is_xsd_namespace(uri):
            return xsd_builtin_types()
        return rng_builtin_types()

    def get_attribute(self, attrs, localname, uri=None):
        if (uri, localname) not in attrs:
            raise LookupError
        return attrs.get((uri, localname))

    @staticmethod
    def noop_handler(attrs, parent_element, factory,
                     schema_path, all_grammars):  # pragma: no cover
        return (parent_element, {})

    @staticmethod
    def rng_div(attrs, parent_element, factory,
                schema_path, all_grammars):
        return (parent_element, {
            'define': prv.rng_define.rng_define,
            'div': factory.rng_div,
            'include': prv.rng_grammar.RngGrammar.rng_include,
            'start': prv.rng_start.rng_start,
        })

    @staticmethod
    def rng_mixed(attrs, parent_element, factory,
                  schema_path, all_grammars):
        assert attrs.getLength() == 0, 'Unexpected attributes in mixed'

        (interleave, dispatcher) = prv.rng_interleave.rng_interleave(
            {}, parent_element, factory, schema_path, all_grammars)

        interleave.children.append(prv.rng_text.RngText({}))

        return (interleave, dispatcher)

    @staticmethod
    def rng_optional(attrs, parent_element, factory,
                     schema_path, all_grammars):
        assert attrs.getLength() == 0, 'Unexpected attributes in optional'

        (choice, dispatcher) = prv.rng_choice.rng_choice(
            {}, parent_element, factory, schema_path, all_grammars)

        choice.children.append(prv.rng_empty.RngEmpty({}))

        return (choice, dispatcher)

    @staticmethod
    def rng_zeroOrMore(attrs, parent_element, factory,
                       schema_path, all_grammars):
        assert attrs.getLength() == 0, 'Unexpected attributes in zeroOrMore'

        (choice, _) = prv.rng_choice.rng_choice(
            {}, parent_element, factory, schema_path, all_grammars)

        choice.children.append(prv.rng_empty.RngEmpty({}))

        (one, dispatcher) = prv.rng_oneOrMore.rng_oneOrMore(
            {}, choice, factory, schema_path, all_grammars)

        return (one, dispatcher)

    def parse_qname(self, qname):
        splitted = qname.split(':')
        if len(splitted) == 1:
            return (None, qname)
        else:
            return (self.namespaces[splitted[0]], splitted[1])


def _is_schema_empty(schema):
    return (not schema.complex_types and
            not schema.simple_types and
            not schema.elements)
