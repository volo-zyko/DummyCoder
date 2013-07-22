# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import checks


class Schema(base.SchemaBase):
    def __init__(self, attrs, schema_path):
        super(Schema, self).__init__(attrs, None)

        self.target_ns = self.attr('targetNamespace')
        self.path = schema_path
        self.prefix = None

        # Containers for elements in the schema.
        self.attributes = {}
        self.complex_types = {}
        self.elements = {}
        self.imports = {}
        self.namespaces = {}
        self.simple_types = {}

        # Temporary containers.
        self.attribute_groups = {}
        self.groups = {}
        self.unnamed_types = []

    def set_namespace(self, prefix, uri):
        self.namespaces[prefix] = uri
        if prefix is not None and uri == self.target_ns:
            self.prefix = prefix

    def set_imports(self, all_schemata):
        self.imports = {
            all_schemata[path].target_ns: all_schemata[path]
            for path in self.imports.keys()}

    @method_once
    def finalize(self, all_schemata, factory):
        for (parents, t) in self.unnamed_types:
            t.finalize(factory)
            t.nameit(parents, factory, set())
            assert t.name is not None, 'Name cannot be None'

            if checks.is_complex_type(t):
                self.complex_types[t.name] = t
            elif checks.is_simple_type(t):
                self.simple_types[t.name] = t
        delattr(self, 'unnamed_types')

        for st in self.simple_types.values():
            st.finalize(factory)
            st.nameit([self], factory, set())

        for ct in self.complex_types.values():
            ct.finalize(factory)
            ct.nameit([self], factory, set())

        for elem in self.elements.values():
            elem.finalize(factory)

        for attr in self.attributes.values():
            attr.finalize(factory)

        super(Schema, self).finalize(None)

    @method_once
    def cleanup(self):
        delattr(self, 'attribute_groups')
        delattr(self, 'groups')
