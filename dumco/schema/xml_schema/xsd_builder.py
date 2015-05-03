# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.base
import dumco.schema.checks as checks
import dumco.schema.model
import dumco.schema.uses as uses
import dumco.schema.xsd_types

import prv.xsd_schema


class XsdElementBuilder(object):
    def __init__(self, arguments, namer):
        # Reset internals of this builder.
        self.reset()

        # These internals should not be reset.
        self.included_schema_paths = {}

        # All prefixes encountered during schemata loading.
        self.all_namespace_prefixes = {dumco.schema.base.XML_NAMESPACE: 'xml'}

        # This is part of the builder's interface.
        self.arguments = arguments
        self.namer = namer
        self.extension = '.xsd'

    def reset(self):
        self.dispatcher_stack = []
        self.dispatcher = {
            'schema': prv.xsd_schema.xsd_schema,
        }
        self.element_stack = []
        self.element = None
        self.namespaces = {'xml': dumco.schema.base.XML_NAMESPACE}
        self.substitution_groups = {}

    def define_namespace(self, prefix, uri):
        if uri is None:
            # Remove namespace.
            assert prefix in self.namespaces, 'Closing non-existent namespace'
            del self.namespaces[prefix]
        else:
            # Add namespace.
            self.namespaces[prefix] = uri

            if (prefix is not None and
                    not checks.is_xsd_namespace(uri)):
                # This makes sure that prefix will be the same no matter
                # what was the order of loading of schemata.
                if prefix > self.all_namespace_prefixes.get(uri, ''):
                    self.all_namespace_prefixes[uri] = prefix

    def new_element(self, elem_name, attrs, schema_path, all_schemata):
        # Here we don't support anything non-XSD.
        if not checks.is_xsd_namespace(elem_name[0]):
            return

        self.dispatcher_stack.append(self.dispatcher)
        self.element_stack.append(self.element)

        assert self.dispatcher is None or elem_name[1] in self.dispatcher, \
            '"{}" is not supported in {}'.format(
                elem_name[1], self.element.__class__.__name__)

        if self.dispatcher is not None:
            xsd_attrs = {name: value for ((uri, name), value) in attrs.items()
                         if uri is None}

            (self.element, self.dispatcher) = self.dispatcher[elem_name[1]](
                xsd_attrs, self.element, self, schema_path, all_schemata)

    def finalize_current_element(self, name):
        # Here we don't support anything non-XSD.
        if not checks.is_xsd_namespace(name[0]):
            return

        self.element = self.element_stack.pop()
        self.dispatcher = self.dispatcher_stack.pop()

    def end_document(self):
        # There might remain single xml namespace.
        assert len(self.namespaces) == 1 or len(self.namespaces) == 0
        assert len(self.dispatcher_stack) == 0
        assert len(self.element_stack) == 0

    def current_element_append_text(self, text):
        self.element.text.append(text)

    def finalize_documents(self, all_schemata):
        def included_in_other_schema(schema):
            for included_paths in self.included_schema_paths.itervalues():
                if schema.path in included_paths:
                    return True
            return False

        sorted_all_schemata = sorted(all_schemata.values(),
                                     key=lambda s: s.dom_element.target_ns)

        # Set schema prefixes and original imports which are necessary during
        # per-schema finalization.
        for schema in sorted_all_schemata:
            schema.set_imports(all_schemata, self)

            schema.dom_element.set_prefix(self.all_namespace_prefixes)

        # Finalize each schema except for those included schemata.
        for schema in sorted_all_schemata:
            if included_in_other_schema(schema):
                continue

            schema.finalize(all_schemata, self)

        # Fix substitution groups. There is no way to do it during schema
        # finalization, so we traverse everything once again.
        substituted = set()
        for schema in sorted_all_schemata:
            self._post_finalize(schema, substituted)

        resulting_schemata = [schema.dom_element
                              for schema in sorted_all_schemata
                              if not included_in_other_schema(schema)]

        self.namer.populate_schema_with_naming(resulting_schemata)

        return resulting_schemata

    def _post_finalize(self, xsd_schema, substituted):
        # for ct in xsd_schema.complex_types:
        #     if ct.abstract:
        #         # Remove abstract complex type.
        #         name = ct.dom_element.name
        #         del xsd_schema.dom_element.complex_types[name]

        # for elem in xsd_schema.elements:
        #     if elem.abstract:
        #         # Remove abstract element.
        #         name = elem.dom_element.term.name
        #         del xsd_schema.dom_element.elements[name]

        def finalize_substitutions(particle):
            for p in particle.traverse():
                if (not checks.is_particle(p) and
                        (p.term not in self.substitution_groups or
                         p.term in substituted)):
                    continue

                substituted.add(p.term)
                p.term = self.substitution_groups[p.term]
                finalize_substitutions(p)

        for ct in xsd_schema.dom_element.complex_types:
            if not checks.has_complex_content(ct):
                continue

            finalize_substitutions(ct.structure)

    def add_substitution_group(self, xsd_head, xsd_element):
        head = xsd_head.dom_element.term

        substitution_group = self.substitution_groups.setdefault(
            head, dumco.schema.model.Choice())

        if not xsd_head.abstract and len(substitution_group.members) == 0:
            substitution_group.members.append(uses.Particle(1, 1, head))

        substitution_group.members.append(
            uses.Particle(1, 1, xsd_element.dom_element.term))

    def add_to_parent_schema(self, element, attrs, schema,
                             fieldname, is_type=False):
        try:
            # Add to parent schema only top-level components or types.
            if isinstance(self.element, prv.xsd_schema.XsdSchema) or is_type:
                name = self.get_attribute(attrs, 'name')
                elements = getattr(schema, fieldname)
                elements[name] = element
        except LookupError:
            assert is_type, 'Only types can be unnamed'

            schema.unnamed_types.append(element)

    def particle_min_occurs(self, attrs):
        return int(self.get_attribute(attrs, 'minOccurs', default='1'))

    def particle_max_occurs(self, attrs):
        max_occurs = self.get_attribute(attrs, 'maxOccurs', default='1')
        return (dumco.schema.base.UNBOUNDED if max_occurs == 'unbounded'
                else int(max_occurs))

    def get_attribute(self, attrs, localname, **kwargs):
        if localname not in attrs:
            if 'default' not in kwargs:
                raise LookupError
            return kwargs['default']
        return attrs.get(localname).strip()

    def resolve_attribute(self, qname, schema):
        (uri, localname) = qname
        if uri is None or uri == schema.dom_element.target_ns:
            return schema.attributes[localname].finalize(self).attribute
        else:
            try:
                attr = schema.imports[uri].attributes[localname]
                return attr.finalize(self).attribute
            except KeyError:
                return dumco.schema.model.xml_attributes()[localname]

    def resolve_attribute_group(self, qname, schema):
        (uri, localname) = qname
        if uri is None or uri == schema.dom_element.target_ns:
            return schema.attribute_groups[localname].finalize(self)
        else:
            attr_group = schema.imports[uri].attribute_groups[localname]
            return attr_group.finalize(self)

    def resolve_complex_type(self, qname, schema, finalize=True):
        (uri, localname) = qname
        if (checks.is_xsd_namespace(uri) and
                localname == 'anyType'):
            return dumco.schema.xsd_types.ct_urtype()

        if uri is None or uri == schema.dom_element.target_ns:
            ct = schema.complex_types[localname]
        else:
            ct = schema.imports[uri].complex_types[localname]

        return (ct.finalize(self) if finalize else ct.dom_element)

    def resolve_element(self, qname, schema):
        (uri, localname) = qname
        if uri is None or uri == schema.dom_element.target_ns:
            elem = schema.elements[localname]
        else:
            elem = schema.imports[uri].elements[localname]

        return elem

    def resolve_group(self, qname, schema):
        (uri, localname) = qname
        if uri is None or uri == schema.dom_element.target_ns:
            return schema.groups[localname].finalize(self)
        else:
            return schema.imports[uri].groups[localname].finalize(self)

    def resolve_simple_type(self, qname, schema):
        (uri, localname) = qname
        if checks.is_xsd_namespace(uri):
            if localname == 'anySimpleType':
                return dumco.schema.xsd_types.st_urtype()
            else:
                return dumco.schema.xsd_types.xsd_builtin_types()[localname]

        if uri is None or uri == schema.dom_element.target_ns:
            st = schema.simple_types[localname]
        else:
            st = schema.imports[uri].simple_types[localname]

        return st.finalize(self)

    def resolve_type(self, qname, schema, finalize):
        try:
            return self.resolve_simple_type(qname, schema)
        except KeyError:
            return self.resolve_complex_type(qname, schema, finalize)

    def parse_qname(self, qname):
        if qname is None:
            return None

        splitted = qname.split(':')
        if len(splitted) == 1:
            if (None in self.namespaces and
                    checks.is_xsd_namespace(self.namespaces[None])):
                return (dumco.schema.xsd_types.XSD_NAMESPACE, qname)
            else:
                return (None, qname)
        else:
            return (self.namespaces[splitted[0]], splitted[1])

    @staticmethod
    def noop_handler(attrs, parent, builder, schema_path, all_schemata):
        return (parent, None)

    @staticmethod
    def xsd_annotation(attrs, parent, builder, schema_path, all_schemata):
        return (parent, {
            'appinfo': builder.noop_handler,
            'documentation': builder.noop_handler,
        })