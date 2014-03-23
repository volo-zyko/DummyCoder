# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.base as base
import dumco.schema.checks as checks
import dumco.schema.elements as elements
import dumco.schema.uses as uses
import dumco.schema.xsd_types as xsd_types

import rng_anyName
import rng_attribute
import rng_choice
import rng_data
import rng_element
import rng_empty
import rng_grammar
import rng_group
import rng_interleave
import rng_list
import rng_name
import rng_nsName
import rng_oneOrMore
import rng_text
import rng_value


class Rng2Model(object):
    def __init__(self, all_schemata, factory):
        self.all_schemata = all_schemata
        self.factory = factory
        self.untyped_elements = {}
        # self.elements_per_schema = {s: {} for s in all_schemata}

    def convert(self, grammar):
        assert isinstance(grammar, rng_grammar.RngGrammar)

        added_elements = set()
        self._convert_start(grammar.start, added_elements)

        for e in grammar.elements:
            if e not in added_elements:
                self._convert_element(e)

        for (pattern, element) in self.untyped_elements.iteritems():
            if _is_complex_pattern(pattern.pattern):
                if not checks.is_any(element):
                    element.type = self._convert_type(
                        pattern.pattern, pattern.define_name, element.schema)
            else:
                element.type = self._convert_simple_type(
                    pattern.pattern, pattern.define_name, element.schema)

    def _convert_start(self, start_pattern, added_elements):
        def convert_root_element(pattern, ns, name, excpt=None):
            assert name is not None, 'Any is not allowed as top-level element'
            added_elements.add(pattern)

            schema = self.all_schemata[ns]
            elem = elements.Element(name, None, None, schema)
            self.untyped_elements[pattern] = elem
            return elem

        def convert_root_elements(pattern):
            if isinstance(pattern, rng_element.RngElement):
                elements = \
                    _convert_named_component(pattern, convert_root_element)

                for e in elements:
                    schema = self.all_schemata[e.schema.target_ns]
                    schema.elements.append(e)
            else:
                for p in pattern.patterns:
                    convert_root_elements(p)

        convert_root_elements(start_pattern.pattern)

    def _convert_element(self, elem_pattern):
        def convert_local_element(pattern, ns, name, excpt=None):
            if name is None and ns is None:
                any_elem = elements.Any([], None)
                self.untyped_elements[pattern] = any_elem
                return any_elem
            elif name is None:
                constraint = elements.Any.Name(ns, None)
                any_elem = elements.Any([constraint], None)
                self.untyped_elements[pattern] = any_elem
                return any_elem
            else:
                elem_schema = self.all_schemata[ns]
                elem = elements.Element(name, None, None, elem_schema)
                self.untyped_elements[pattern] = elem
                return elem

        _convert_named_component(elem_pattern, convert_local_element)

    def _convert_simple_type(self, type_pattern, component_name, schema):
        type_name = '{}-type'.format(component_name)

        if isinstance(type_pattern, rng_empty.RngEmpty):
            t = elements.SimpleType(type_name, schema)
            schema.simple_types.append(t)

            t.restriction = elements.Restriction(schema)
            t.restriction.base = xsd_types.xsd_builtin_types()['string']
            t.restriction.length = '0'

            return t
        elif isinstance(type_pattern, rng_value.RngValue):
            # assert type_pattern.value is not None

            # return elements.EnumerationValue(type_pattern.value, '')
            return xsd_types.xsd_builtin_types()['string']
        elif isinstance(type_pattern, rng_text.RngText):
            return xsd_types.xsd_builtin_types()['string']
        elif isinstance(type_pattern, rng_data.RngData):
            if not type_pattern.params and type_pattern.except_pattern is None:
                return type_pattern.type

            t = elements.SimpleType(type_name, schema)
            schema.simple_types.append(t)

            t.restriction = elements.Restriction(schema)
            t.restriction.base = type_pattern.type
            _set_restriction_params(type_pattern, t.restriction)
            # if type_pattern.except_pattern is not None:
            #     assert False, 'Not implemented'

            return t
        elif isinstance(type_pattern, rng_list.RngList):
            t = elements.SimpleType(type_name, schema)
            schema.simple_types.append(t)

            t.listitems.append(
                elements.ListTypeCardinality(
                    self._convert_simple_type(type_pattern.data_pattern,
                                              None, schema),
                    0, base.UNBOUNDED))

            return t
        elif isinstance(type_pattern, rng_choice.RngChoicePattern):
            t = elements.SimpleType(type_name, schema)
            schema.simple_types.append(t)

            # has_empty = False
            enum_types = {}

            for p in type_pattern.patterns:
                if isinstance(p, rng_empty.RngEmpty):
                    pass
                    # has_empty = True
                elif isinstance(p, rng_oneOrMore.RngOneOrMore):
                    pass
                elif isinstance(p, rng_value.RngValue):
                    type_key = '{}:{}'.format(p.datatypes_uri, p.type.name)
                    enum_type = enum_types.get(type_key, None)
                    if enum_type is None:
                        enum_type_name = \
                            '{}-choice{}'.format(type_name, len(enum_types))
                        enum_type = elements.SimpleType(enum_type_name, schema)
                        enum_type.restriction = elements.Restriction(schema)
                        enum_type.restriction.base = p.type

                    enum_type.restriction.enumeration.append(
                        elements.EnumerationValue(p.value, ''))
                elif isinstance(p, rng_data.RngData):
                    t.union.append(p.type)

            return t
        elif isinstance(type_pattern, rng_interleave.RngInterleave):
            pass

    def _convert_type(self, type_pattern, element_name, element_schema):
        t = elements.ComplexType('{}-type'.format(element_name),
                                 element_schema)
        element_schema.complex_types.append(t)
        struct = self._convert_type_structure(type_pattern, element_schema)
        if checks.is_particle(struct):
            t.structure = struct
        else:
            t.structure = uses.Particle(False, 1, 1, struct)
        return t

    def _convert_type_structure(self, type_pattern, element_schema):
        def convert_compositor(compositor):
            required = True
            multiple = False
            for p in type_pattern.patterns:
                if isinstance(p, rng_empty.RngEmpty):
                    required = False
                    continue
                elif isinstance(type_pattern, rng_oneOrMore.RngOneOrMore):
                    multiple = True
                    assert len(p.patterns) == 1
                    p = p.patterns[0]

                struct = self._convert_type_structure(p, element_schema)
                if isinstance(struct, list):
                    for a in struct:
                        assert checks.is_attribute(a) or checks.is_any(a)
                        constraint = base.ValueConstraint(False, None)
                        compositor.members.append(
                            uses.AttributeUse(False, constraint, required, a))
                elif (checks.is_particle(struct) or
                        checks.is_attribute_use(struct)):
                    compositor.members.append(struct)
                else:
                    min_occurs = 1 if required else 0
                    max_occurs = base.UNBOUNDED if multiple else 1
                    compositor.members.append(
                        uses.Particle(False, min_occurs, max_occurs, struct))

            if len(compositor.members) == 1:
                return compositor.members[0]

            return compositor

        if isinstance(type_pattern, rng_attribute.RngAttribute):
            def convert_attribute(pattern, ns, name, excpt=None):
                if name is None and ns is None:
                    any_attr = elements.Any([], element_schema)
                    return any_attr
                elif name is None:
                    constraint = elements.Any.Name(ns, None)
                    any_attr = elements.Any([constraint], element_schema)
                    return any_attr
                else:
                    schema = self.all_schemata[ns]
                    attribute = elements.Attribute(name, None, None, schema)
                    attribute.type = self._convert_simple_type(
                        pattern.pattern, name, schema)
                    return attribute

            return _convert_named_component(type_pattern, convert_attribute)
        elif isinstance(type_pattern, rng_element.RngElement):
            elem = self.untyped_elements[type_pattern]
            if checks.is_any(elem):
                elem.schema = element_schema
            return elem
        elif isinstance(type_pattern, rng_choice.RngChoicePattern):
            choice = elements.Choice(element_schema)
            return convert_compositor(choice)
        # elif isinstance(type_pattern, rng_oneOrMore.RngOneOrMore):
        #     return
        elif isinstance(type_pattern, rng_group.RngGroup):
            sequence = elements.Sequence(element_schema)
            return convert_compositor(sequence)
        elif isinstance(type_pattern, rng_interleave.RngInterleave):
            allp = elements.All(element_schema)
            return convert_compositor(allp)


def _convert_named_component(elem_or_attr_pattern, convert_func):
    assert (isinstance(elem_or_attr_pattern, rng_element.RngElement) or
            isinstance(elem_or_attr_pattern, rng_attribute.RngAttribute))

    def handle_name_class(name):
        if isinstance(name, rng_name.RngName):
            return [convert_func(elem_or_attr_pattern, name.ns, name.name)]
        elif isinstance(name, rng_anyName.RngAnyName):
            return [convert_func(elem_or_attr_pattern, None, None,
                                 excpt=name.except_name_class)]
        elif isinstance(name, rng_nsName.RngNsName):
            return [convert_func(elem_or_attr_pattern, name.ns, None,
                                 excpt=name.except_name_class)]
        elif isinstance(name, rng_choice.RngChoiceName):
            result = []
            for n in name.name_classes:
                assert not isinstance(n, rng_choice.RngChoiceName)

                result.append(handle_name_class(n))

            return result

    return handle_name_class(elem_or_attr_pattern.name)


def _is_complex_pattern(pattern):
    if (isinstance(pattern, rng_choice.RngChoicePattern) or
            isinstance(pattern, rng_group.RngGroup) or
            isinstance(pattern, rng_interleave.RngInterleave) or
            isinstance(pattern, rng_oneOrMore.RngOneOrMore)):
        for p in pattern.patterns:
            if _is_complex_pattern(p):
                return True
    elif (isinstance(pattern, rng_attribute.RngAttribute) or
            isinstance(pattern, rng_element.RngElement)):
        return True

    return False


def _set_restriction_params(data, restriction):
    if checks.is_xsd_namespace(data.datatypes_uri):
        return

    for p in data.params:
        if p.name == 'fractionDigits':
            restriction.fraction_digits = p.value
        elif p.name == 'length':
            restriction.length = p.value
        elif p.name == 'maxExclusive':
            restriction.max_exclusive = p.value
        elif p.name == 'maxInclusive':
            restriction.max_inclusive = p.value
        elif p.name == 'maxLength':
            restriction.max_length = p.value
        elif p.name == 'minExclusive':
            restriction.min_exclusive = p.value
        elif p.name == 'minInclusive':
            restriction.min_inclusive = p.value
        elif p.name == 'minLength':
            restriction.min_length = p.value
        elif p.name == 'pattern':
            restriction.pattern = p.value
        elif p.name == 'totalDigits':
            restriction.total_digits = p.value
        elif p.name == 'whiteSpace':
            restriction.white_space = p.value
        else:
            assert False, '{} is not allowed as restriction ' \
                'in XML Schema'.format(p.name)
