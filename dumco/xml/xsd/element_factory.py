# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.base
import dumco.schema.checks
import dumco.schema.elements
import dumco.schema.enums

import prv.xsd_schema


class XsdElementFactory(object):
    def __init__(self, element_namer):
        # Reset internals of this factory.
        self.reset()

        # These internals should not be reset.
        self.included_schema_paths = {}
        # Either path to XSD file or XSD as StringIO.
        self.current_xsd = None

        # All prefices encountered during schemata loading.
        self.all_namespace_prefices = {dumco.schema.checks.XML_NAMESPACE: 'xml'}

        # Set part of the factorie's interface.
        self.namer = element_namer
        self.extension = '.xsd'

    def reset(self, element_namer=None):
        self.dispatcher_stack = []
        self.dispatcher = {
            'schema': prv.xsd_schema.xsd_schema,
        }
        self.element_stack = []
        self.element = None
        self.namespaces = {'xml': dumco.schema.checks.XML_NAMESPACE}
        self.substitution_groups = {}

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
        # Here we don't support anything non-XSD.
        if not dumco.schema.checks.is_xsd_namespace(name[0]):
            return

        self.dispatcher_stack.append(self.dispatcher)
        self.element_stack.append(self.element)

        assert self.dispatcher is None or name[1] in self.dispatcher, \
            '"{}" is not supported in {}'.format(
                name[1], self.element.__class__.__name__)

        if self.dispatcher is not None:
            xsd_attrs = {}
            for ((uri, n), value) in attrs.items():
                # XML Schema attributes are always unqualified.
                if uri is not None:
                    continue

                # This way we make sure that all XSD attributes with QName
                # value and which we want to process will have correctly
                # resolved namespace uri.
                if (n == 'ref' or n == 'type' or n == 'base' or
                    n == 'substitutionGroup' or n == 'itemType'):
                    xsd_attrs[n] = self._parse_qname(value)
                elif n == 'memberTypes':
                    xsd_attrs[n] = [self._parse_qname(q)
                        for q in value.split()]
                else:
                    xsd_attrs[n] = value

            (element, self.dispatcher) = self.dispatcher[name[1]](
                xsd_attrs, self.element, self, schema_path, all_schemata)

            self.element = element

    def finalize_current_element(self, name):
        # Here we don't support anything non-XSD.
        if not dumco.schema.checks.is_xsd_namespace(name[0]):
            return

        self.element = self.element_stack.pop()
        self.dispatcher = self.dispatcher_stack.pop()

    def end_document(self):
        self.current_xsd = None

        # There might remain single xml namespace.
        assert len(self.namespaces) == 1 or len(self.namespaces) == 0
        assert len(self.dispatcher_stack) == 0
        assert len(self.element_stack) == 0

    def current_element_append_text(self, text):
        if hasattr(self.element, 'schema_element'):
            self.element.schema_element.append_doc(text)

    def finalize_documents(self, all_schemata):
        # Set original imports which are necessary during
        # per-schema finalization.
        for schema in all_schemata.itervalues():
            schema.set_imports(all_schemata)

            schema.schema_element.set_prefix(self.all_namespace_prefices)

        def included_in_other_schema(schema):
            for included_paths in self.included_schema_paths.itervalues():
                if schema.schema_element.path in included_paths:
                    return True
            return False

        # Finalize each schema.
        for schema in sorted(all_schemata.itervalues(),
                             key=lambda s: s.schema_element.target_ns):
            if included_in_other_schema(schema):
                continue

            schema.finalize(all_schemata, self)

        # Set prefix and imports in each DOM schema.
        for schema in all_schemata.itervalues():
            def enum_schema_content_n_substitute(schema_element):
                for ct in schema_element.complex_types.itervalues():
                    for (_, p) in dumco.schema.enums.enum_ct_particles(ct):
                        yield p.term

                    for (_, u) in dumco.schema.enums.enum_attribute_uses(ct):
                        yield u.attribute

                    if dumco.schema.checks.has_simple_content(ct):
                        yield ct.text.type

                for st in schema_element.simple_types.itervalues():
                    yield st

                for elem in schema_element.elements.itervalues():
                    yield elem

                for attr_use in schema_element.attribute_uses.itervalues():
                    yield attr_use.attribute

            def add_import_if_differ(own_schema, other_schema):
                if other_schema is not None and other_schema != own_schema:
                    own_schema.add_import(other_schema)
                    return True
                return False

            schema_element = schema.schema_element
            for c in enum_schema_content_n_substitute(schema_element):
                if add_import_if_differ(schema_element, c.schema):
                    continue

                if (dumco.schema.checks.is_element(c) or
                    dumco.schema.checks.is_attribute(c)):
                    add_import_if_differ(schema_element, c.type.schema)
                elif dumco.schema.checks.is_simple_type(c):
                    if c.restriction is not None:
                        add_import_if_differ(schema_element,
                                             c.restriction.base.schema)
                    elif c.listitem is not None:
                        add_import_if_differ(schema_element, c.listitem.schema)
                    elif c.union:
                        for s in c.union:
                            add_import_if_differ(schema_element, s.schema)

        return {path: schema.schema_element
                for (path, schema) in all_schemata.iteritems()
                if not included_in_other_schema(schema)}

    def add_to_parent_schema(self, element, attrs, schema,
                             fieldname, is_type=False):
        try:
            # Add to parent schema only top-level components or types.
            if isinstance(self.element, prv.xsd_schema.XsdSchema) or is_type:
                name = self.get_attribute(attrs, 'name')
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

            assert is_type, 'Only types can be unnamed'

            parents = reduce(fold_elements, self.element_stack, [])
            assert parents, 'parents list should be longer than 0'
            schema.unnamed_types.append((parents, element))

    def particle_min_occurs(self, attrs):
        try:
            min_occurs = self.get_attribute(attrs, 'minOccurs')
            return int(min_occurs)
        except LookupError:
            return 1

    def particle_max_occurs(self, attrs):
        try:
            max_occurs = self.get_attribute(attrs, 'maxOccurs')
            return (dumco.schema.base.UNBOUNDED if max_occurs == 'unbounded'
                    else int(max_occurs))
        except LookupError:
            return 1

    def attribute_default(self, attrs):
        try:
            return self.get_attribute(attrs, 'default')
        except LookupError:
            return None

    def attribute_required(self, attrs):
        try:
            return self.get_attribute(attrs, 'use') == 'required'
        except LookupError:
            return None

    def resolve_attribute(self, (uri, localname), schema, finalize=False):
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

    def resolve_attribute_group(self, (uri, localname), schema):
        if uri is None or uri == schema.schema_element.target_ns:
            return schema.attribute_groups[localname].finalize(self)
        else:
            attr_group = schema.imports[uri].attribute_groups[localname]
            return attr_group.finalize(self)

    def resolve_complex_type(self, (uri, localname), schema, finalize=False):
        if (dumco.schema.checks.is_xsd_namespace(uri) and
            localname == 'anyType'):
            return dumco.schema.elements.ComplexType.urtype()

        if uri is None or uri == schema.schema_element.target_ns:
            ct = schema.complex_types[localname]
            return (ct.finalize(self) if finalize else ct.schema_element)
        else:
            ct = schema.imports[uri].complex_types[localname]
            return (ct.finalize(self) if finalize else ct.schema_element)

    def resolve_element(self, (uri, localname), schema, finalize=False):
        if uri is None or uri == schema.schema_element.target_ns:
            elem = schema.elements[localname]
            return (elem.finalize(self).term if finalize
                    else elem.schema_element.term)
        else:
            elem = schema.imports[uri].elements[localname]
            return (elem.finalize(self).term if finalize
                    else elem.schema_element.term)

    def resolve_group(self, (uri, localname), schema):
        if uri is None or uri == schema.schema_element.target_ns:
            return schema.groups[localname].finalize(self)
        else:
            return schema.imports[uri].groups[localname].finalize(self)

    def resolve_simple_type(self, (uri, localname), schema, finalize=False):
        if dumco.schema.checks.is_xsd_namespace(uri):
            if localname == 'anySimpleType':
                return dumco.schema.elements.SimpleType.urtype()
            else:
                return dumco.schema.base.xsd_builtin_types()[localname]

        if uri is None or uri == schema.schema_element.target_ns:
            st = schema.simple_types[localname]
            return (st.finalize(self) if finalize else st.schema_element)
        else:
            st = schema.imports[uri].simple_types[localname]
            return (st.finalize(self) if finalize else st.schema_element)

    def resolve_type(self, qname, schema, finalize=False):
        try:
            return self.resolve_simple_type(qname, schema, finalize=finalize)
        except KeyError:
            return self.resolve_complex_type(qname, schema, finalize=finalize)

    def get_attribute(self, attrs, localname):
        if localname not in attrs:
            raise LookupError
        return attrs.get(localname)

    def _parse_qname(self, qname):
        splitted = qname.split(':')
        if len(splitted) == 1:
            if (None in self.namespaces and
                dumco.schema.checks.is_xsd_namespace(self.namespaces[None])):
                return (dumco.schema.checks.XSD_NAMESPACE, qname)
            else:
                return (None, qname)
        else:
            return (self.namespaces[splitted[0]], splitted[1])

    @staticmethod
    def noop_handler(attrs, parent_element, factory,
                     schema_path, all_schemata):
        return (parent_element, None)

    @staticmethod
    def xsd_annotation(attrs, parent_element, factory,
                       schema_path, all_schemata):
        return (parent_element, {
            'appinfo': factory.noop_handler,
            'documentation': factory.noop_handler,
        })
