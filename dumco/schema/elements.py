# Distributed under the GPLv2 License; see accompanying file COPYING.

import collections

from dumco.utils.decorators import method_once, function_once

import base
import checks
import namer
import uses
import xsd_types


@function_once
def xml_attributes():
    attrs = {name: uses.AttributeUse(None, False, False, False,
                                     Attribute(name, None))
             for name in ['base', 'id', 'lang', 'space']}

    attrs['base'].attribute.type = xsd_types.xsd_builtin_types()['anyURI']

    attrs['id'].attribute.type = xsd_types.xsd_builtin_types()['ID']

    attrs['lang'].attribute.type = xsd_types.xsd_builtin_types()['language']

    # spaceType is an artificial name, it's not defined by any specs.
    space_type = SimpleType('spaceType', None)
    space_type.restriction = Restriction(None)
    space_type.restriction.base = xsd_types.xsd_builtin_types()['NCName']
    space_type.restriction.enumeration = [
        EnumerationValue('default', ''), EnumerationValue('preserve', '')]
    attrs['space'].attribute.type = space_type
    attrs['space'].constraint = base.ValueConstraint(False, 'preserve')

    return attrs


class Interleave(base.Compositor):
    pass


class Any(base.DataComponent):
    # Any can have type and a list of constraints. If the list of constraints
    # is empty then Any accepts any name in any namespace. Otherwise list
    # contains an interleaving of Name and Not tuples.
    # Name tuple has ns and tag fields which contain strings with respective
    # meanings. Either ns or tag must be None (but not both) and in this case
    # any restricts either namespace or tag.
    # Not tuple has only name field which contains instance of Name tuple.
    # This means anything except for the name.

    Name = collections.namedtuple('Name', ['ns', 'tag'])
    Not = collections.namedtuple('Not', ['name'])

    def __init__(self, constraints, parent_schema):
        super(Any, self).__init__(None, parent_schema)

        for c in constraints:
            if isinstance(c, Any.Name):
                assert ((c.ns is None and c.tag is not None) or
                        (c.tag is None and c.ns is not None)), \
                    'Either namespace or tag must be a wildcard'
            elif isinstance(c, Any.Not):
                assert c.name.ns is not None or c.name.tag is not None, \
                    'Incorrect \'Not\' constraint'

        self.constraints = constraints


class Attribute(base.DataComponent):
    def __init__(self, name, parent_schema):
        super(Attribute, self).__init__(name, parent_schema)


class Choice(base.Compositor):
    pass


class ComplexType(base.SchemaBase):
    # ComplexType uses structure member for its content representation.
    # The structure is comprised of a sequence with min and max ocurrs
    # equal to 1 and which contains in order: 1) list of attributes (can
    # be empty); 2) particle which is a content with markup of a given
    # ComplexType (can be missing); 3) textual content (can be missing).
    # If neither of the above 3 parts is present then structure has value None.
    # If ComplexType has both particle and text then its content is mixed.
    # If there is no attributes and text in ComplexType but particle is
    # non-empty then structure contains that particle (the wrapping sequence
    # is left out).

    def __init__(self, name, parent_schema):
        super(ComplexType, self).__init__(parent_schema)

        self.structure = None
        self.name = name

    @property
    def mixed(self):
        has_markup = False
        for _ in self.particles(flatten=True):
            has_markup = True
            break

        return self.text().component is not None and has_markup

    def attribute_uses(self):
        for x in self.traverse_structure_with_parents(flatten=True):
            if checks.is_attribute_use(x.component):
                yield x

    def particles(self, flatten=True):
        for x in self.traverse_structure_with_parents(flatten=flatten):
            if checks.is_particle(x.component):
                yield x

    def text(self):
        for x in self.traverse_structure_with_parents(flatten=True):
            if checks.is_text(x.component):
                return x
        return base.ChildComponent(self, None)

    def traverse_structure_with_parents(self, flatten=True):
        # This function generates a sequence of pairs of data elements and
        # their parents. It can happen that it generates nothing.
        if self.structure is not None:
            if not flatten:
                yield base.ChildComponent(self, self.structure)

            term = self.structure.term
            for x in term.traverse_with_parents(flatten=flatten):
                yield x

    @staticmethod
    @function_once
    def urtype():
        seqpart = uses.Particle(False, 1, 1, Sequence(None))
        seqpart.term.members.append(
            uses.Particle(False, 1, base.UNBOUNDED, Any([], None)))

        root_seqpart = uses.Particle(False, 1, 1, Sequence(None))
        root_seqpart.term.members.append(
            uses.AttributeUse(None, False, False, False, Any([], None)))
        root_seqpart.term.members.append(seqpart)
        root_seqpart.term.members.append(
            uses.SchemaText(xsd_types.xsd_builtin_types()['string']))

        urtype = ComplexType('anyType', None)
        urtype.structure = root_seqpart
        return urtype

    @method_once
    def nameit(self, parents, factory, names):
        namer.forge_name(self, parents, factory, names)

        if self.structure is not None:
            self.structure.nameit(parents + [self], factory, names)
            assert self.structure.name is not None, 'Name cannot be None'


class Element(base.DataComponent):
    def __init__(self, name, default, fixed, parent_schema):
        super(Element, self).__init__(name, parent_schema)

        self.constraint = base.ValueConstraint(fixed, default)


EnumerationValue = collections.namedtuple('EnumerationValue', ['value', 'doc'])


class Restriction(base.SchemaBase):
    # white_space member can take any of these values.
    WS_PRESERVE = 1
    WS_REPLACE = 2
    WS_COLLAPSE = 3

    def __init__(self, parent_schema):
        super(Restriction, self).__init__(parent_schema)

        # Base type is always a primitive type.
        # List is restricted in its own way.
        self.base = None

        # Facets.
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
    def __init__(self, target_ns):
        super(Schema, self).__init__(None)

        self.target_ns = target_ns
        self.prefix = None
        self.filename = None

        # Member imports references other schemata elements from which
        # are used in this schema. It potentially can reference schemata
        # that are not directly used by this schema but which are necessary
        # for correct dumping of attributes that belong to this schema.
        self.imports = {}
        # Containers for elements in the schema.
        self.elements = []
        self.complex_types = []
        self.simple_types = []

    def set_prefix(self, all_namespace_prefixes):
        if self.target_ns in all_namespace_prefixes:
            self.prefix = all_namespace_prefixes[self.target_ns]

    def add_import(self, schema):
        if schema is None or checks.is_xml_namespace(schema.target_ns):
            # Schema can be None if it's predefined XML schema.
            self.imports[base.XML_NAMESPACE] = None
            return

        assert (schema.target_ns not in self.imports or
                self.imports[schema.target_ns] == schema), \
            'Redefining namespace to a different schema'

        self.imports[schema.target_ns] = schema


class Sequence(base.Compositor):
    pass


class SimpleType(base.SchemaBase):
    def __init__(self, name, parent_schema):
        super(SimpleType, self).__init__(parent_schema)

        self.name = name
        # Instance of Restriction.
        self.restriction = None
        # List of instances of ListTypeCardinality with simple (which
        # includes unions and potentially lists) or native types inside.
        # Each of the list items is matched in the input string in order.
        self.listitems = []
        # List of simple of native types. The first matching type for an
        # input string is assumed to be its type.
        self.union = []

    @staticmethod
    @function_once
    def urtype():
        urtype = SimpleType('anySimpleType', None)

        restr = Restriction(None)
        restr.base = ComplexType.urtype()
        urtype.restriction = restr

        return urtype

    @method_once
    def nameit(self, parents, factory, names):
        namer.forge_name(self, parents, factory, names)
