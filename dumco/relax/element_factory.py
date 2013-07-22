# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.all
import dumco.schema.any
import dumco.schema.attribute
import dumco.schema.base
import dumco.schema.choice
import dumco.schema.complex_type
import dumco.schema.element
import dumco.schema.restriction
import dumco.schema.schema
import dumco.schema.sequence
import dumco.schema.simple_type
import dumco.schema.checks
import dumco.schema.uses


class RelaxElementFactory(object):
    def __init__(self, element_namer):
        # Internals of this factory.
        self.dispatcher_stack = []
        self.dispatcher = {
            'grammar': RelaxElementFactory._grammar,
        }
        self.namespaces = {'xml': dumco.schema.checks.XML_NAMESPACE}
        self.all_named_ns = {dumco.schema.checks.XML_NAMESPACE: 'xml'}
        self.parents = []

        # Part of the factorie's interface.
        self.namer = element_namer
        self.extension = '.rng'

        self.simple_types = {x: dumco.schema.base.XsdNativeType(x)
                             for x in dumco.schema.base.NATIVE_XSD_TYPE_NAMES}

        self.xml_attributes = {x: dumco.schema.base.XmlAttribute(x)
                               for x in ['base', 'id', 'lang', 'space']}

        self.complex_urtype = dumco.schema.complex_type.ComplexType.urtype(self)
        self.simple_urtype = dumco.schema.simple_type.SimpleType.urtype(self)

    def open_namespace(self, prefix, uri):
        self.namespaces[prefix] = uri

        # if prefix is not None and not dumco.schema.checks.is_xsd_namespace(uri):
        #     assert (not self.all_named_ns.has_key(uri) or
        #             self.all_named_ns[uri] == prefix), \
        #         'Namespace prefix {0} is already defined as {1}'.format(
        #             prefix, self.all_named_ns[uri])
        #     self.all_named_ns[uri] = prefix

    def close_namespace(self, prefix):
        assert self.namespaces.has_key(prefix), \
            'Closing non-existent namespace'
        del self.namespaces[prefix]

    def new_element(self, name, attrs, parent_element,
                    schema_path, all_schemata):
        # # Here we don't support anything non-XSD.
        # assert name[0] == dumco.schema.checks.XSD_NAMESPACE, \
        #     'Uknown elment {0}:{1}'.format(name[0], name[1])

        self.dispatcher_stack.append(self.dispatcher)

        assert self.dispatcher.has_key(name[1]), \
            '"{0}" is not supported in {1}'.format(
                name[1], parent_element.__class__.__name__)

        (element, self.dispatcher) = self.dispatcher[name[1]](
            self, attrs, parent_element, schema_path, all_schemata)

        try:
            self.parents.append(element[1])
            return element[0]
        except TypeError:
            self.parents.append(element)
            return element

    def finalize_element(self, element):
        self.dispatcher = self.dispatcher_stack.pop()
        self.parents.pop()

    def element_append_text(self, element, text):
        element.append_doc(text)

    def finalize_documents(self, all_schemata):
        for schema in all_schemata.itervalues():
            schema.set_imports(all_schemata)

            if self.all_named_ns.has_key(schema.target_ns):
                schema.set_namespace(self.all_named_ns[schema.target_ns],
                                     schema.target_ns)

        for schema in all_schemata.itervalues():
            schema.finalize(all_schemata, self)

        for schema in all_schemata.itervalues():
            schema.cleanup()

    def get_attribute(self, attrs, localname, uri=None):
        if not attrs.has_key((uri, localname)):
            raise LookupError
        return attrs.get((uri, localname))

    def _noop_handler(self, attrs, parent_element,
                      schema_path, all_schemata):
        return (parent_element, {
            # 'element': RelaxElementFactory._noop_handler,
            # 'empty': RelaxElementFactory._noop_handler,
            # 'optional': RelaxElementFactory._noop_handler,
            # 'ref': RelaxElementFactory._ref,
        })

    def _attribute(self, attrs, parent_element,
                   schema_path, all_schemata):
        return (parent_element, {
            'data': RelaxElementFactory._noop_handler,
        })

    def _define(self, attrs, parent_element,
                schema_path, all_schemata):
        return (parent_element, {
            'attribute': RelaxElementFactory._attribute,
            'element': RelaxElementFactory._element,
            'optional': RelaxElementFactory._optional,
            'ref': RelaxElementFactory._ref,
        })

    def _choice(self, attrs, parent_element,
                schema_path, all_schemata):
        return (parent_element, {
            'group': RelaxElementFactory._group,
            'ref': RelaxElementFactory._ref,
            'zeroOrMore': RelaxElementFactory._zeroOrMore,
        })

    def _element(self, attrs, parent_element,
                 schema_path, all_schemata):
        return (parent_element, {
            'attribute': RelaxElementFactory._attribute,
            'choice': RelaxElementFactory._choice,
            'data': RelaxElementFactory._noop_handler,
            'empty': RelaxElementFactory._noop_handler,
            'oneOrMore': RelaxElementFactory._oneOrMore,
            'optional': RelaxElementFactory._optional,
            'ref': RelaxElementFactory._ref,
            'zeroOrMore': RelaxElementFactory._zeroOrMore,
        })

    def _grammar(self, attrs, parent_element,
                 schema_path, all_schemata):
        schema = dumco.schema.schema.Schema(attrs, schema_path)
        all_schemata[schema_path] = schema
        for (prefix, uri) in self.namespaces.iteritems():
            schema.set_namespace(prefix, uri)

        return (schema, {
            'define': RelaxElementFactory._define,
            'include': RelaxElementFactory._noop_handler,
            'start': RelaxElementFactory._start,
        })

    def _group(self, attrs, parent_element,
               schema_path, all_schemata):
        return (parent_element, {
            'zeroOrMore': RelaxElementFactory._zeroOrMore,
        })

    def _oneOrMore(self, attrs, parent_element,
                   schema_path, all_schemata):
        return (parent_element, {
            'choice': RelaxElementFactory._choice,
            'element': RelaxElementFactory._element,
            'ref': RelaxElementFactory._ref,
        })

    def _optional(self, attrs, parent_element,
                  schema_path, all_schemata):
        return (parent_element, {
            'element': RelaxElementFactory._element,
            'ref': RelaxElementFactory._ref,
        })

    def _ref(self, attrs, parent_element,
             schema_path, all_schemata):
        return (parent_element, {
            # 'element': RelaxElementFactory._element,
            # 'ref': RelaxElementFactory._ref,
        })

    def _start(self, attrs, parent_element,
               schema_path, all_schemata):
        return (parent_element, {
            'element': RelaxElementFactory._element,
        })

    def _zeroOrMore(self, attrs, parent_element,
                    schema_path, all_schemata):
        return (parent_element, {
            'choice': RelaxElementFactory._choice,
            'element': RelaxElementFactory._element,
            'ref': RelaxElementFactory._ref,
        })
