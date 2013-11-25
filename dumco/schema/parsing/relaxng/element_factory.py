# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.base
import dumco.schema.checks
import dumco.schema.elements
import dumco.schema.enums
import dumco.schema.uses

import prv.rng_grammar


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
        # Here we don't support anything non-RelaxNG.
        if name[0] != RNG_NAMESPACE:
            return

        self.dispatcher_stack.append(self.dispatcher)
        self.element_stack.append(self.element)

        assert self.dispatcher is None or name[1] in self.dispatcher, \
            '"{}" is not supported in {}'.format(
                name[1], self.element.__class__.__name__)

        if self.dispatcher is not None:
            (element, self.dispatcher) = self.dispatcher[name[1]](
                attrs, self.element, self, schema_path, all_schemata)

            self.element = element

    def finalize_current_element(self, name):
        if name[0] != RNG_NAMESPACE:
            return

        self.element = self.element_stack.pop()
        self.dispatcher = self.dispatcher_stack.pop()

    def end_document(self):
        # There might remain single xml namespace.
        assert len(self.namespaces) == 1 or len(self.namespaces) == 0
        assert len(self.dispatcher_stack) == 0
        assert len(self.element_stack) == 0

    def current_element_append_text(self, text):
        if hasattr(self.element, 'schema_element'):
            self.element.schema_element.append_doc(text)

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

    # def get_attribute(self, attrs, localname, uri=None):
    #     if not attrs.has_key((uri, localname)):
    #         raise LookupError
    #     return attrs.get((uri, localname))

    @staticmethod
    def noop_handler(attrs, parent_element, factory, schema_path, all_schemata):
        return (parent_element, {
            # 'element': RelaxElementFactory._noop_handler,
            # 'empty': RelaxElementFactory._noop_handler,
            # 'optional': RelaxElementFactory._noop_handler,
            # 'ref': RelaxElementFactory._ref,
        })
