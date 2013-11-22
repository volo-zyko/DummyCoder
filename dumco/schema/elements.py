# Distributed under the GPLv2 License; see accompanying file COPYING.

import collections

from dumco.utils.decorators import method_once, function_once

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
    def __init__(self, name, default, fixed, parent_schema):
        super(Attribute, self).__init__(parent_schema)

        self.name = name
        self.type = None
        self.constraint = base.ValueConstraint(
            True if fixed else False, fixed if fixed else default)


class Choice(base.SchemaBase):
    def __init__(self, parent_schema):
        super(Choice, self).__init__(parent_schema)

        self.particles = []
        self.attribute_uses = []


class ComplexType(base.SchemaBase):
    def __init__(self, name, parent_schema):
        super(ComplexType, self).__init__(parent_schema)

        self.name = name
        self.attribute_uses = []
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

        seqpart = uses.Particle(None, 1, 1, Sequence(None))
        anypart = uses.Particle(None, 1, base.UNBOUNDED, Any(Any.ANY, None))
        anyattr = uses.AttributeUse(None, None, None, Any(Any.ANY, None))

        seqpart.term.particles.append(anypart)
        urtype.particle = seqpart
        urtype.text = base.SchemaText(base.xsd_builtin_types()['string'])
        urtype.attribute_uses.append(anyattr)

        return urtype

    @method_once
    def nameit(self, parents, factory, names):
        namer.forge_name(self, parents, factory, names)

        if self.particle is not None:
            self.particle.nameit(parents + [self], factory, names)
            assert self.particle.name is not None, \
                'Name cannot be None'


class Element(base.SchemaBase):
    def __init__(self, name, default, fixed, parent_schema):
        super(Element, self).__init__(parent_schema)

        self.name = name
        self.type = None
        self.constraint = base.ValueConstraint(
            True if fixed else False, fixed if fixed else default)


EnumerationValue = collections.namedtuple('EnumerationValue', ['value', 'doc'])


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
        self.attributes = []
        self.complex_types = []
        self.elements = []
        self.imports = {}
        self.simple_types = []

    def set_prefix(self, all_namespace_prefices):
        if self.target_ns in all_namespace_prefices:
            self.prefix = all_namespace_prefices[self.target_ns]

    def add_import(self, schema):
        if schema is None:
            # Schema can be None if it's predefined XML schema.
            self.imports[base.XML_NAMESPACE] = None
            return

        assert (schema.target_ns not in self.imports or
                self.imports[schema.target_ns] == schema), \
            'Redefining namespace to a different schema'

        self.imports[schema.target_ns] = schema


class Sequence(base.SchemaBase):
    def __init__(self, parent_schema):
        super(Sequence, self).__init__(parent_schema)

        self.particles = []


class SimpleType(base.SchemaBase):
    def __init__(self, name, parent_schema):
        super(SimpleType, self).__init__(parent_schema)

        self.name = name
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
