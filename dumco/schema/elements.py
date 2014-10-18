# Distributed under the GPLv2 License; see accompanying file COPYING.

import collections
import itertools

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
    def equal_content(self, other):
        if (not checks.is_choice(other) or
                len(self.members) != len(other.members)):
            return False

        return True


class ComplexType(base.SchemaBase):
    # ComplexType uses structure member for its content representation.
    # The structure is comprised of a sequence with min and max occurs
    # equal to 1 and which contains in order: 1) list of attributes (can
    # be empty); 2) particle which is a content with markup of a given
    # ComplexType (can be missing); 3) textual content (can be missing).
    # If neither of the above 3 parts is present then structure has value None.
    # If ComplexType has both particle and text then its content is mixed.

    def __init__(self, name, parent_schema):
        super(ComplexType, self).__init__(parent_schema)

        self.structure = None
        self.name = name

    @property
    def mixed(self):
        for _ in self.particles():
            return self.text() is not None
        else:
            return False

    def attribute_uses(self, flatten=True):
        for x in self.traverse_structure(flatten=flatten):
            if ((flatten and checks.is_attribute_use(x)) or
                    (not flatten and checks.is_attribute_use(x.component))):
                yield x

    def text(self, flatten=True):
        for x in self.traverse_structure(flatten=flatten):
            if ((flatten and checks.is_text(x)) or
                    (not flatten and checks.is_text(x.component))):
                return x
        return None

    def particles(self, flatten=True):
        for x in self.traverse_structure(flatten=flatten):
            if ((flatten and checks.is_particle(x)) or
                    (not flatten and checks.is_particle(x.component))):
                yield x

    def traverse_structure(self, flatten=True):
        # This function generates a sequence of pairs of data elements and
        # their parents. It can happen that it generates nothing.
        if self.structure is None:
            return

        assert (checks.is_particle(self.structure) and
                checks.is_compositor(self.structure.term))

        if flatten:
            for x in self.structure.traverse():
                yield x
        else:
            for x in self.structure.traverse(flatten=False, parents=[self]):
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

    def equal_content(self, other):
        # No need to call parent's equal_content() since types must not
        # necessarily belong to one schema.
        if self.structure is None and other.structure is None:
            return True

        return self.structure.equal_content(other.structure)

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

    def equal_content(self, other):
        eq = super(Element, self).equal_content(other)

        return eq and self.constraint == other.constraint


EnumerationValue = collections.namedtuple('EnumerationValue', ['value', 'doc'])


class Interleave(base.Compositor):
    def equal_content(self, other):
        if (not checks.is_interleave(other) or
                len(self.members) != len(other.members)):
            return False

        return True


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

    def equal_content(self, other):
        def enums_equal(e1, e2):
            return e1.value == e2.value

        if other is None:
            return False
        if not self.base.equal_content(other.base):
            return False
        elif not equal_permutations(
                self.enumeration, other.enumeration, enums_equal):
            return False
        elif self.fraction_digits != other.fraction_digits:
            return False
        elif self.length != other.length:
            return False
        elif self.max_exclusive != other.max_exclusive:
            return False
        elif self.max_inclusive != other.max_inclusive:
            return False
        elif self.max_length != other.max_length:
            return False
        elif self.min_exclusive != other.min_exclusive:
            return False
        elif self.min_inclusive != other.min_inclusive:
            return False
        elif self.min_length != other.min_length:
            return False
        elif self.pattern != other.pattern:
            return False
        elif self.total_digits != other.total_digits:
            return False
        elif self.white_space != other.white_space:
            return False

        return True


class Schema(base.SchemaBase):
    def __init__(self, target_ns):
        super(Schema, self).__init__(None)

        self.filename = None
        self.prefix = None
        self.target_ns = target_ns

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
    def equal_content(self, other):
        if (not checks.is_sequence(other) or
                len(self.members) != len(other.members)):
            return False

        for (m1, m2) in zip(self.members):
            if not m1.equal_content(m2):
                return False

        return True


class SimpleType(base.SchemaBase):
    def __init__(self, name, parent_schema):
        super(SimpleType, self).__init__(parent_schema)

        self.name = name

        # List of instances of ListTypeCardinality with simple (which
        # includes unions and potentially lists) or native types inside.
        # Each of the list items is matched in the input string in order.
        self.listitems = []
        # Instance of Restriction.
        self.restriction = None
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

    def equal_content(self, other):
        def union_members_equal(e1, e2):
            return e1.equal_content(e2)

        # No need to call parent's equal_content() since types must not
        # necessarily belong to one schema.
        if (self.restriction is not None and
                self.restriction.equal_content(other.restriction)):
            return True
        elif len(self.listitems) == len(other.listitems):
            for (li1, li2) in zip(self.listitems, other.listitems):
                if (li1.min_occurs != li2.min_occurs or
                        li1.max_occurs != li2.max_occurs or
                        not li1.type.equal_content(li2.type)):
                    return False
            return True
        elif equal_permutations(self.union, other.union, union_members_equal):
            return True

        return False

    @method_once
    def nameit(self, parents, factory, names):
        namer.forge_name(self, parents, factory, names)


def equal_permutations(list1, list2, items_equal):
    if len(list1) != len(list2):
        return False

    # The first permutation is equal to list2.
    for permutation in itertools.permutation(list2):
        if all([items_equal(x, y) for (x, y) in zip(list1, permutation)]):
            return True

    return False
