# Distributed under the GPLv2 License; see accompanying file COPYING.

import collections

from dumco.utils.decorators import function_once

import base
import checks
import xsd_types


@function_once
def xml_attributes():
    attrs = {name: Attribute(name, None, False, False, xml_schema())
             for name in ['base', 'id', 'lang', 'space']}

    attrs['base'].type = xsd_types.xsd_builtin_types()['anyURI']

    attrs['id'].type = xsd_types.xsd_builtin_types()['ID']

    attrs['lang'].type = xsd_types.xsd_builtin_types()['language']

    # spaceType is an artificial name, it's not defined by any specs.
    space_type = SimpleType('spaceType', xml_schema())
    space_type.restriction = Restriction()
    space_type.restriction.base = xsd_types.xsd_builtin_types()['NCName']
    space_type.restriction.enumerations = [
        EnumerationValue('default', ''), EnumerationValue('preserve', '')]
    attrs['space'].type = space_type
    attrs['space'].constraint = base.ValueConstraint('preserve', False)

    return attrs


@function_once
def xml_schema():
    return Schema(base.XML_NAMESPACE, 'xml')


class Any(base.DataComponent):
    # Any can have type and one constraint. If constraint is None then Any
    # accepts any name in any namespace. Otherwise the constraint is either
    # Name or Not tuple.
    # Name tuple has ns and tag fields which contain strings with respective
    # meanings. Either ns or tag must be None (but not both) and in this case
    # any restricts either namespace or tag.
    # Not tuple has only name field which contains instance of Name tuple,
    # which means anything except for the name.

    Name = collections.namedtuple('Name', ['ns', 'tag'])
    Not = collections.namedtuple('Not', ['name'])

    def __init__(self, constraint, parent_schema):
        super(Any, self).__init__(None, None, False, False, parent_schema)

        assert not isinstance(constraint, list)

        if isinstance(constraint, Any.Name):
            assert ((constraint.ns is None and constraint.tag is not None) or
                    (constraint.tag is None and constraint.ns is not None)), \
                'Either namespace or tag must be a wildcard'
        elif isinstance(constraint, Any.Not):
            assert (constraint.name.ns is not None or
                    constraint.name.tag is not None), \
                'Incorrect \'Not\' constraint'

        self.constraint = constraint


class Attribute(base.DataComponent):
    def __init__(self, name, default, fixed, qualified, parent_schema):
        super(Attribute, self).__init__(name, default, fixed,
                                        qualified, parent_schema)


class Choice(base.Compositor):
    pass


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
        for x in self.traverse_structure(flatten):
            if ((flatten and checks.is_attribute_use(x)) or
                    (not flatten and checks.is_attribute_use(x.component))):
                yield x

    def text(self, flatten=True):
        for x in self.traverse_structure(flatten):
            if ((flatten and checks.is_text(x)) or
                    (not flatten and checks.is_text(x.component))):
                return x
        return None

    def particles(self, flatten=True):
        for x in self.traverse_structure(flatten):
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


class Element(base.DataComponent):
    def __init__(self, name, default, fixed, qualified, parent_schema):
        super(Element, self).__init__(name, default, fixed,
                                      qualified, parent_schema)


EnumerationValue = collections.namedtuple('EnumerationValue', ['value', 'doc'])


class Interleave(base.Compositor):
    pass


class Restriction(base.SchemaBase):
    # white_space member can take any of these values.
    WS_PRESERVE = 1
    WS_REPLACE = 2
    WS_COLLAPSE = 3

    def __init__(self):
        super(Restriction, self).__init__(None)

        # Base type is always a primitive type.
        # List is restricted in its own way.
        self.base = None

        # Facets.
        self.enumerations = []
        self.fraction_digits = None
        self.length = None
        self.max_exclusive = None
        self.max_inclusive = None
        self.max_length = None
        self.min_exclusive = None
        self.min_inclusive = None
        self.min_length = None
        self.patterns = []
        self.total_digits = None
        self.white_space = None


class Schema(base.SchemaBase):
    def __init__(self, target_ns, prefix=None):
        super(Schema, self).__init__(None)

        self.filename = None
        self.prefix = prefix
        self.target_ns = target_ns

        # Containers for elements in the schema.
        self.elements = []
        self.complex_types = []
        self.simple_types = []

    def set_prefix(self, all_namespace_prefixes):
        if self.target_ns in all_namespace_prefixes:
            self.prefix = all_namespace_prefixes[self.target_ns]


class Sequence(base.Compositor):
    pass


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
