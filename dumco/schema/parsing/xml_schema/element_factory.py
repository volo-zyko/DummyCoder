# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.base
import dumco.schema.checks
import dumco.schema.elements
import dumco.schema.enums
import dumco.schema.uses
import dumco.schema.xsd_types

import prv.xsd_schema


class XsdElementFactory(object):
    def __init__(self, arguments, namer):
        # Reset internals of this factory.
        self.reset()

        # These internals should not be reset.
        self.included_schema_paths = {}

        # All prefixes encountered during schemata loading.
        self.all_namespace_prefixes = {dumco.schema.base.XML_NAMESPACE: 'xml'}

        # This is part of the factory's interface.
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
                    not dumco.schema.checks.is_xsd_namespace(uri)):
                # This makes sure that prefix will be the same no matter
                # what was the order of loading of schemata.
                if prefix > self.all_namespace_prefixes.get(uri, ''):
                    self.all_namespace_prefixes[uri] = prefix

    def new_element(self, elem_name, attrs, schema_path, all_schemata):
        # Here we don't support anything non-XSD.
        if not dumco.schema.checks.is_xsd_namespace(elem_name[0]):
            return

        self.dispatcher_stack.append(self.dispatcher)
        self.element_stack.append(self.element)

        assert self.dispatcher is None or elem_name[1] in self.dispatcher, \
            '"{}" is not supported in {}'.format(
                elem_name[1], self.element.__class__.__name__)

        if self.dispatcher is not None:
            xsd_attrs = {}
            for ((uri, name), value) in attrs.items():
                # XML Schema attributes are always unqualified.
                if uri is not None:
                    continue

                # This way we make sure that all XSD attributes with QName
                # value and which we want to process will have correctly
                # resolved namespace uri.
                if (name == 'ref' or name == 'type' or name == 'base' or
                        name == 'substitutionGroup' or name == 'itemType'):
                    xsd_attrs[name] = self._parse_qname(value)
                elif name == 'memberTypes':
                    xsd_attrs[name] = [
                        self._parse_qname(q) for q in value.split()]
                else:
                    xsd_attrs[name] = value

            (self.element, self.dispatcher) = self.dispatcher[elem_name[1]](
                xsd_attrs, self.element, self, schema_path, all_schemata)

    def finalize_current_element(self, name):
        # Here we don't support anything non-XSD.
        if not dumco.schema.checks.is_xsd_namespace(name[0]):
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
        def included_in_other_schema(schema):
            for included_paths in self.included_schema_paths.itervalues():
                if schema.path in included_paths:
                    return True
            return False

        sorted_all_schemata = sorted(all_schemata.values(),
                                     key=lambda s: s.schema_element.target_ns)

        # Set schema prefixes and original imports which are necessary during
        # per-schema finalization.
        for schema in sorted_all_schemata:
            schema.set_imports(all_schemata, self)

            schema.schema_element.set_prefix(self.all_namespace_prefixes)

        # Finalize each schema except for those included schemata.
        for schema in sorted_all_schemata:
            if included_in_other_schema(schema):
                continue

            schema.finalize(all_schemata, self)

        # Set imports in each DOM schema and fix substitution groups.
        # There is no way to do it during schema finalization, so we traverse
        # everything once again.
        substituted = set()
        for schema in sorted_all_schemata:
            self._post_finalize(schema, substituted)

        return [schema.schema_element
                for schema in sorted_all_schemata
                if not included_in_other_schema(schema)]

    def _post_finalize(self, xsd_schema, substituted):
        checks = dumco.schema.checks

        def enum_schema_content_with_fixes(schema):
            def enum_with_substitute(particle):
                for p in particle.traverse():
                    if not checks.is_particle(p):
                        continue

                    if (p.term in self.substitution_groups and
                            p.term not in substituted):
                        substituted.add(p.term)
                        p.term = self.substitution_groups[p.term]
                        for t in enum_with_substitute(p):
                            yield t
                    else:
                        yield p.term

            # for ct in schema.complex_types:
            #     if ct.abstract:
            #         # Remove abstract complex type.
            #         name = ct.schema_element.name
            #         del schema.schema_element.complex_types[name]

            # for elem in schema.elements:
            #     if elem.abstract:
            #         # Remove abstract element.
            #         name = elem.schema_element.term.name
            #         del schema.schema_element.elements[name]

            for ct in schema.schema_element.complex_types:
                if ct.mixed or checks.has_complex_content(ct):
                    for t in enum_with_substitute(ct.structure):
                        yield t

                for u in ct.attribute_uses():
                    yield u.attribute

                if checks.has_simple_content(ct):
                    yield ct.text().type

            for st in schema.schema_element.simple_types:
                yield st

            for elem in schema.schema_element.elements:
                yield elem

        def add_import_if_differ(own_schema, other_schema):
            if own_schema != other_schema:
                own_schema.add_import(other_schema)
                return True
            return False

        # Traverse all schema components and add imports if necessary.
        for c in enum_schema_content_with_fixes(xsd_schema):
            if add_import_if_differ(xsd_schema.schema_element, c.schema):
                if checks.is_attribute(c):
                    add_import_if_differ(c.schema, c.type.schema)

                continue

            if checks.is_element(c) or checks.is_attribute(c):
                add_import_if_differ(xsd_schema.schema_element,
                                     c.type.schema)
            elif checks.is_simple_type(c):
                if c.restriction is not None:
                    add_import_if_differ(xsd_schema.schema_element,
                                         c.restriction.base.schema)
                elif c.listitems:
                    for s in c.listitems:
                        add_import_if_differ(xsd_schema.schema_element,
                                             s.type.schema)
                elif c.union:
                    for s in c.union:
                        add_import_if_differ(xsd_schema.schema_element,
                                             s.schema)

    def add_substitution_group(self, xsd_head, xsd_element):
        head = xsd_head.schema_element.term

        if head not in self.substitution_groups:
            self.substitution_groups[head] = \
                dumco.schema.elements.Choice(head.schema)
        substitution_group = self.substitution_groups[head]

        if not xsd_head.abstract and len(substitution_group.members) == 0:
            substitution_group.members.append(dumco.schema.uses.Particle(
                xsd_head.qualified, 1, 1, head))

        substitution_group.members.append(dumco.schema.uses.Particle(
            xsd_element.qualified, 1, 1, xsd_element.schema_element.term))

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

    def resolve_attribute(self, qname, schema, finalize=False):
        (uri, localname) = qname
        if uri is None or uri == schema.schema_element.target_ns:
            attr = schema.attributes[localname]
            if finalize:
                attr = attr.finalize(self)
            return attr.schema_element
        else:
            try:
                attr = schema.imports[uri].attributes[localname]
                if finalize:
                    attr = attr.finalize(self)
                return attr.schema_element
            except KeyError:
                return dumco.schema.elements.xml_attributes()[localname]

    def resolve_attribute_group(self, qname, schema):
        (uri, localname) = qname
        if uri is None or uri == schema.schema_element.target_ns:
            return schema.attribute_groups[localname].finalize(self)
        else:
            attr_group = schema.imports[uri].attribute_groups[localname]
            return attr_group.finalize(self)

    def resolve_complex_type(self, qname, schema, finalize=False):
        (uri, localname) = qname
        if (dumco.schema.checks.is_xsd_namespace(uri) and
                localname == 'anyType'):
            return dumco.schema.elements.ComplexType.urtype()

        if uri is None or uri == schema.schema_element.target_ns:
            ct = schema.complex_types[localname]
            return (ct.finalize(self) if finalize else ct.schema_element)
        else:
            ct = schema.imports[uri].complex_types[localname]
            return (ct.finalize(self) if finalize else ct.schema_element)

    def resolve_element(self, qname, schema, finalize=False):
        (uri, localname) = qname
        if uri is None or uri == schema.schema_element.target_ns:
            elem = schema.elements[localname]
            return (elem, elem.finalize(self).term if finalize
                    else elem.schema_element.term)
        else:
            elem = schema.imports[uri].elements[localname]
            return (elem, elem.finalize(self).term if finalize
                    else elem.schema_element.term)

    def resolve_group(self, qname, schema):
        (uri, localname) = qname
        if uri is None or uri == schema.schema_element.target_ns:
            return schema.groups[localname].finalize(self)
        else:
            return schema.imports[uri].groups[localname].finalize(self)

    def resolve_simple_type(self, qname, schema, finalize=False):
        (uri, localname) = qname
        if dumco.schema.checks.is_xsd_namespace(uri):
            if localname == 'anySimpleType':
                return dumco.schema.elements.SimpleType.urtype()
            else:
                return dumco.schema.xsd_types.xsd_builtin_types()[localname]

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
        checks = dumco.schema.checks

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
