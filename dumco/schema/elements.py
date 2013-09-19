# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once, function_once
import dumco.utils.string_utils

import base
import namer
import uses


class All(base.SchemaBase):
    def __init__(self, parent_schema):
        super(All, self).__init__(parent_schema)

        self.particles = []


class Any(base.SchemaBase):
    ANY = 1
    OTHER = 2

    def __init__(self, namespace, parent_schema):
        super(Any, self).__init__(parent_schema)

        # Either ANY, OTHER or list of URIs.
        self.namespace = namespace


class Attribute(base.SchemaBase):
    def __init__(self, name, qualified, parent_schema):
        super(Attribute, self).__init__(parent_schema)

        self.name = name
        self.type = None
        self.qualified = qualified


class Choice(base.SchemaBase):
    def __init__(self, parent_schema):
        super(Choice, self).__init__(parent_schema)

        self.particles = []


class ComplexType(base.SchemaBase):
    def __init__(self, name, parent_schema):
        super(ComplexType, self).__init__(parent_schema)

        self.name = (name if name == 'anyType' or name is None
                     else dumco.utils.string_utils.upper_first_letter(name))
        self.attributes = []
        self.particle = None
        self.text = None

    @property
    def mixed(self):
        return (self.particle is not None and
                self.text is not None)

    @staticmethod
    @function_once
    def urtype():
        urtype = ComplexType('anyType', None)

        seqpart = uses.Particle(1, 1, Sequence(None))
        anypart = uses.Particle(1, base.UNBOUNDED, Any(Any.ANY, None))
        anyattr = uses.AttributeUse(None, None, Any(Any.ANY, None))

        seqpart.term.particles.append(anypart)
        urtype.particle = seqpart
        urtype.text = base.SchemaText(base.xsd_builtin_types()['string'])
        urtype.attributes.append(anyattr)

        return urtype

    @method_once
    def nameit(self, parents, factory, names):
        namer.forge_name(self, parents, factory, names)

        if self.particle is not None:
            self.particle.nameit(parents + [self], factory, names)
            assert self.particle.name is not None, \
                'Name cannot be None'


class Element(base.SchemaBase):
    def __init__(self, name, qualified, parent_schema):
        super(Element, self).__init__(parent_schema)

        self.name = name
        self.type = None
        self.qualified = qualified


class Restriction(base.SchemaBase):
    WS_PRESERVE = 1
    WS_REPLACE = 2
    WS_COLLAPSE = 3

    def __init__(self, parent_schema):
        super(Restriction, self).__init__(parent_schema)

        # Either primitive type or simple type with list/union content.
        self.base = None
        self.enumeration = []
        self.fraction_digits = None
        self.length = None
        self.max_exclusive = None
        self.max_inclusive = None
        self.max_length = None
        self.min_exclusive = None
        self.min_inclusive = None
        self.min_length = None
        self.pattern = None
        self.total_digits = None
        self.white_space = None


class Schema(base.SchemaBase):
    def __init__(self, target_ns, schema_path):
        super(Schema, self).__init__(None)

        self.target_ns = target_ns
        self.path = schema_path
        self.prefix = None

        # Containers for elements in the schema.
        self.attributes = {}
        self.complex_types = {}
        self.elements = {}
        self.imports = {}
        self.namespaces = {}
        self.simple_types = {}

    def set_namespace(self, prefix, uri):
        self.namespaces[prefix] = uri
        if prefix is not None and uri == self.target_ns:
            self.prefix = prefix

    def set_imports(self, import_paths, all_schemata):
        self.imports = {
            all_schemata[path].target_ns: all_schemata[path]
            for path in import_paths}


class Sequence(base.SchemaBase):
    def __init__(self, parent_schema):
        super(Sequence, self).__init__(parent_schema)

        self.particles = []


class SimpleType(base.SchemaBase):
    def __init__(self, name, parent_schema):
        super(SimpleType, self).__init__(parent_schema)

        self.name = (name if name == 'anySimpleType' or name is None
                     else dumco.utils.string_utils.upper_first_letter(name))
        self.restriction = None
        self.listitem = None
        self.union = []

    @staticmethod
    def urtype():
        urtype = SimpleType('anySimpleType', None)

        restr = Restriction(None)
        restr.base = ComplexType.urtype()
        urtype.restriction = restr

        return urtype

    @method_once
    def nameit(self, parents, factory, names):
        namer.forge_name(self, parents, factory, names)
