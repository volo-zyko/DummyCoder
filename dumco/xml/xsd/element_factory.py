# Distributed under the GPLv2 License; see accompanying file COPYING.

import os.path

import dumco.schema.base
import dumco.schema.checks
import dumco.schema.elements

import prv.xsd_schema


class XsdElementFactory(object):
    def __init__(self, element_namer):
        # Internals of this factory.
        self.dispatcher_stack = []
        self.dispatcher = {
            'schema': prv.xsd_schema.xsd_schema,
        }
        self.element_stack = []
        self.element = None
        self.namespaces = {'xml': dumco.schema.checks.XML_NAMESPACE}
        self.all_named_ns = {dumco.schema.checks.XML_NAMESPACE: 'xml'}

        # Part of the factorie's interface.
        self.namer = element_namer
        self.extension = '.xsd'

    def open_namespace(self, prefix, uri):
        self.namespaces[prefix] = uri

        if prefix is not None and not dumco.schema.checks.is_xsd_namespace(uri):
            assert (uri not in self.all_named_ns or
                    self.all_named_ns[uri] == prefix), \
                'Namespace prefix {0} is already defined as {1}'.format(
                    prefix, self.all_named_ns[uri])
            self.all_named_ns[uri] = prefix

    def close_namespace(self, prefix):
        assert prefix in self.namespaces, \
            'Closing non-existent namespace'
        del self.namespaces[prefix]

    def new_element(self, name, attrs, schema_path, all_schemata):
        # Here we don't support anything non-XSD.
        if not dumco.schema.checks.is_xsd_namespace(name[0]):
            return

        self.dispatcher_stack.append(self.dispatcher)
        self.element_stack.append(self.element)

        assert name[1] in self.dispatcher, \
            '"{0}" is not supported in {1}'.format(
                name[1], self.element.__class__.__name__)

        (element, self.dispatcher) = self.dispatcher[name[1]](
            attrs, self.element, self, schema_path, all_schemata)

        self.element = element

    def finalize_current_element(self):
        self.element = self.element_stack.pop()
        self.dispatcher = self.dispatcher_stack.pop()

    def current_element_append_text(self, text):
        if hasattr(self.element, 'schema_element'):
            self.element.schema_element.append_doc(text)

    def finalize_documents(self, all_schemata):
        for schema in all_schemata.itervalues():
            schema.set_imports(all_schemata)

            if schema.schema_element.target_ns in self.all_named_ns:
                schema.schema_element.set_namespace(
                    self.all_named_ns[schema.schema_element.target_ns],
                    schema.schema_element.target_ns)

        for schema in sorted(all_schemata.itervalues(),
                             key=lambda s: s.schema_element.target_ns):
            schema.finalize(all_schemata, self)

        return {path: schema.schema_element
                for (path, schema) in all_schemata.iteritems()}

    def add_to_parent_schema(self, element, attrs, schema,
                             fieldname, is_type=False):
        try:
            name = self._get_attribute(attrs, 'name')
            assert name is not None, 'Name cannot be None'

            elements = getattr(schema, fieldname)
            elements[name] = element
        except LookupError:
            def fold_elements(accum, e):
                checks = dumco.schema.checks
                if hasattr(e, 'schema_element'):
                    if checks.is_particle(e.schema_element):
                        return accum + [e.schema_element.term]
                    elif checks.is_attribute_use(e.schema_element):
                        return accum + [e.schema_element.attribute]
                    elif (checks.is_complex_type(e.schema_element) or
                          checks.is_simple_type(e.schema_element)):
                        return accum + [e.schema_element]
                return accum

            if is_type:
                parents = reduce(fold_elements, self.element_stack, [])
                assert parents, 'parents list should be longer than 0'
                schema.unnamed_types.append((parents, element))

    def particle_min_occurs(self, attrs):
        try:
            min_occurs = self._get_attribute(attrs, 'minOccurs')
            return int(min_occurs)
        except LookupError:
            return 1

    def particle_max_occurs(self, attrs):
        try:
            max_occurs = self._get_attribute(attrs, 'maxOccurs')
            return (dumco.schema.base.UNBOUNDED if max_occurs == 'unbounded'
                    else int(max_occurs))
        except LookupError:
            return 1

    def attribute_default(self, attrs):
        try:
            return self._get_attribute(attrs, 'default')
        except LookupError:
            return None

    def attribute_required(self, attrs):
        try:
            return self._get_attribute(attrs, 'use') == 'required'
        except LookupError:
            return None

    def resolve_attribute(self, qname, schema, finalize=False):
        (uri, localname) = self._parse_qname(
            qname, schema.schema_element.namespaces)
        if uri is None or uri == schema.schema_element.target_ns:
            attr = schema.attributes[localname]
            return (attr.finalize(self).attribute if finalize
                    else attr.schema_element.attribute)
        else:
            try:
                attr = schema.imports[uri].attributes[localname]
                return (attr.finalize(self).attribute if finalize
                        else attr.schema_element.attribute)
            except KeyError:
                return dumco.schema.base.xml_attributes()[localname]

    def resolve_attribute_group(self, qname, schema):
        (uri, localname) = self._parse_qname(
            qname, schema.schema_element.namespaces)
        if uri is None or uri == schema.schema_element.target_ns:
            return schema.attribute_groups[localname].finalize(self)
        else:
            attr_grp = schema.imports[uri].attribute_groups[localname]
            return attr_grp.finalize(self)

    def resolve_complex_type(self, qname, schema, finalize=False):
        (uri, localname) = self._parse_qname(
            qname, schema.schema_element.namespaces)
        if uri is None or uri == schema.schema_element.target_ns:
            ct = schema.complex_types[localname]
            return (ct.finalize(self) if finalize else ct.schema_element)
        else:
            ct = schema.imports[uri].complex_types[localname]
            return (ct.finalize(self) if finalize else ct.schema_element)

    def resolve_element(self, qname, schema, finalize=False):
        (uri, localname) = self._parse_qname(
            qname, schema.schema_element.namespaces)
        if uri is None or uri == schema.schema_element.target_ns:
            elem = schema.elements[localname]
            return (elem.finalize(self).term if finalize
                    else elem.schema_element.term)
        else:
            elem = schema.imports[uri].elements[localname]
            return (elem.finalize(self).term if finalize
                    else elem.schema_element.term)

    def resolve_group(self, qname, schema):
        (uri, localname) = self._parse_qname(
            qname, schema.schema_element.namespaces)
        if uri is None or uri == schema.schema_element.target_ns:
            return schema.groups[localname].finalize(self)
        else:
            return schema.imports[uri].groups[localname].finalize(self)

    def resolve_simple_type(self, qname, schema, finalize=False):
        (uri, localname) = self._parse_qname(
            qname, schema.schema_element.namespaces)
        if uri is None or uri == schema.schema_element.target_ns:
            st = schema.simple_types[localname]
            return (st.finalize(self) if finalize else st.schema_element)
        else:
            if dumco.schema.checks.is_xsd_namespace(uri):
                return dumco.schema.base.xsd_builtin_types()[localname]

            st = schema.imports[uri].simple_types[localname]
            return (st.finalize(self) if finalize else st.schema_element)

    def resolve_type(self, qname, schema, finalize=False):
        try:
            return self.resolve_simple_type(qname, schema, finalize=finalize)
        except KeyError:
            return self.resolve_complex_type(qname, schema, finalize=finalize)

    def _get_attribute(self, attrs, localname, uri=None):
        if (uri, localname) not in attrs:
            raise LookupError
        return attrs.get((uri, localname))

    def _parse_qname(self, qname, namespaces, default=''):
        splitted = qname.split(':')
        if len(splitted) == 1:
            return (None, qname)
        else:
            return (namespaces[splitted[0]], splitted[1])

    @staticmethod
    def noop_handler(attrs, parent_element, factory,
                     schema_path, all_schemata):
        return (parent_element, {
            'appinfo': factory.noop_handler,
            'documentation': factory.noop_handler,
            'field': factory.noop_handler,
            'selector': factory.noop_handler,
        })

    @staticmethod
    def _value_handler(fieldname, attrs, parent_element, factory,
                       schema_path, all_schemata):
        assert hasattr(parent_element.schema_element, fieldname)
        setattr(parent_element.schema_element, fieldname,
                factory._get_attribute(attrs, 'value'))

        return (parent_element, {
            'annotation': factory.noop_handler,
        })

    @staticmethod
    def xsd_annotation(attrs, parent_element, factory,
                       schema_path, all_schemata):
        return (parent_element, {
            'documentation': factory._xsd_documentation,
        })

    @staticmethod
    def _xsd_documentation(attrs, parent_element, factory,
                           schema_path, all_schemata):
        return (parent_element, None)

    @staticmethod
    def xsd_import(attrs, parent_element, factory,
                   schema_path, all_schemata):
        try:
            location = factory._get_attribute(attrs, 'schemaLocation')
        except LookupError:
            location = None

        namespace = factory._get_attribute(attrs, 'namespace')

        if location is not None:
            new_schema_path = os.path.realpath(
                os.path.join(os.path.dirname(schema_path), location))

            assert (os.path.isfile(new_schema_path) or
                    namespace == dumco.schema.checks.XML_NAMESPACE), \
                'File {0} does not exist'.format(new_schema_path)

            if os.path.isfile(new_schema_path):
                all_schemata[new_schema_path] = all_schemata[new_schema_path] \
                    if new_schema_path in all_schemata else None
                all_schemata[schema_path].imports[new_schema_path] = None

        return (parent_element, {
            'annotation': XsdElementFactory.noop_handler,
        })

    xsd_length = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdElementFactory._value_handler('length', attrs,
            parent_element, factory, schema_path, all_schemata)

    xsd_maxExclusive = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdElementFactory._value_handler('max_exclusive', attrs,
            parent_element, factory, schema_path, all_schemata)

    xsd_maxInclusive = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdElementFactory._value_handler('max_inclusive', attrs,
            parent_element, factory, schema_path, all_schemata)

    xsd_maxLength = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdElementFactory._value_handler('max_length', attrs,
            parent_element, factory, schema_path, all_schemata)

    xsd_minExclusive = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdElementFactory._value_handler('min_exclusive', attrs,
            parent_element, factory, schema_path, all_schemata)

    xsd_minInclusive = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdElementFactory._value_handler('min_inclusive', attrs,
            parent_element, factory, schema_path, all_schemata)

    xsd_minLength = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdElementFactory._value_handler('min_length', attrs,
            parent_element, factory, schema_path, all_schemata)

    xsd_pattern = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdElementFactory._value_handler('pattern', attrs,
            parent_element, factory, schema_path, all_schemata)
