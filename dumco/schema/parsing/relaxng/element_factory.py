# Distributed under the GPLv2 License; see accompanying file COPYING.

import itertools

import dumco.schema.base
import dumco.schema.checks
import dumco.schema.xsd_types

import prv.rng_choice
import prv.rng_empty
import prv.rng_interleave
import prv.rng_grammar
import prv.rng_oneOrMore
import prv.rng_text


RNG_NAMESPACE = 'http://relaxng.org/ns/structure/1.0'


class RelaxElementFactory(object):
    def __init__(self, element_namer, extension):
        # Reset internals of this factory.
        self.reset()

        # All prefices encountered during schemata loading.
        self.all_namespace_prefices = {dumco.schema.base.XML_NAMESPACE: 'xml'}

        # Part of the factorie's interface.
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
            assert prefix in self.namespaces, \
                'Closing non-existent namespace'
            del self.namespaces[prefix]
        else:
            # Add namespace.
            self.namespaces[prefix] = uri

        if prefix is not None and not dumco.schema.checks.is_xsd_namespace(uri):
            # This makes sure that prefix will be the same no matter what was
            # the order of loading of schemata.
            if prefix > self.all_namespace_prefices.get(uri, ''):
                self.all_namespace_prefices[uri] = prefix

    def new_element(self, name, attrs, schema_path, all_schemata):
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
        except LookupError:
            self.ns_attribute_stack.append(None)

        assert self.dispatcher is None or name[1] in self.dispatcher, \
            '"{}" is not supported in {}'.format(
                name[1], self.element.__class__.__name__)

        if self.dispatcher is not None:
            (self.element, self.dispatcher) = self.dispatcher[name[1]](
                attrs, self.element, self, schema_path, all_schemata)

    def finalize_current_element(self, name):
        self.element = self.element_stack.pop()

        # Here we don't support anything non-RelaxNG.
        if name[0] != RNG_NAMESPACE:
            return

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

    def finalize_documents(self, all_schemata):
        result = reduce(lambda acc, g: acc + g.schemata,
                        all_schemata.itervalues(), [])
        result.sort(key=lambda x: x.target_ns)
        return result

        # sorted_all_schemata = sorted([schema for schema in
        #                               all_schemata.itervalues()],
        #                              key=lambda s: s.schema_element.target_ns)

        # for schema in sorted_all_schemata:
        #     schema.set_imports(all_schemata)

            # if self.all_named_ns.has_key(schema.target_ns):
            #     schema.set_namespace(self.all_named_ns[schema.target_ns],
            #                          schema.target_ns)

        # for schema in sorted_all_schemata:
        #     schema.finalize(all_schemata, self)

        # for schema in sorted_all_schemata:
        #     schema.cleanup()
        # return [schema.schema_element
        #         for schema in sorted_all_schemata
        #         if not included_in_other_schema(schema)]

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
            return dumco.schema.xsd_types.xsd_builtin_types()
        return {}

    def get_attribute(self, attrs, localname, uri=None):
        if not attrs.has_key((uri, localname)):
            raise LookupError
        return attrs.get((uri, localname))

    @staticmethod
    def noop_handler(attrs, parent_element, factory,
                     schema_path, all_schemata):
        return (parent_element, {})

    @staticmethod
    def rng_mixed(attrs, parent_element, factory,
                  schema_path, all_schemata):
        assert attrs.getLength() == 0, 'Unexpected attributes in mixed'

        (interleave, dispatcher) = prv.rng_interleave.rng_interleave(
            {}, parent_element, factory, schema_path, all_schemata)

        interleave.children.append(prv.rng_text.RngText({}, schema_path))

        return (interleave, dispatcher)

    @staticmethod
    def rng_optional(attrs, parent_element, factory,
                     schema_path, all_schemata):
        assert attrs.getLength() == 0, 'Unexpected attributes in optional'

        (choice, dispatcher) = prv.rng_choice.rng_choice(
            {}, parent_element, factory, schema_path, all_schemata)

        choice.children.append(prv.rng_empty.RngEmpty({}, schema_path))

        return (choice, dispatcher)

    @staticmethod
    def rng_zeroOrMore(attrs, parent_element, factory,
                       schema_path, all_schemata):
        assert attrs.getLength() == 0, 'Unexpected attributes in zeroOrMore'

        (choice, _) = prv.rng_choice.rng_choice(
            {}, parent_element, factory, schema_path, all_schemata)

        (one, dispatcher) = prv.rng_oneOrMore.rng_oneOrMore(
            {}, choice, factory, schema_path, all_schemata)

        choice.children.append(choice)
        choice.children.append(prv.rng_empty.RngEmpty({}, schema_path))

        return (one, dispatcher)
