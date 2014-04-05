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
        self.added_elements = set()
        self.untyped_elements = {}
        self.unique_type_names = set()
        self.unique_type_counter = 0
        # self.elements_per_schema = {s: {} for s in all_schemata}

    def convert(self, grammar):
        assert isinstance(grammar, rng_grammar.RngGrammar)

        self._convert_start(grammar.start)

        element_set = set(self.added_elements)
        remaining = element_set
        while remaining:
            for e in sorted(remaining, key=lambda e: e.define_name):
                self._convert_element(e)

            new_element_set = set(self.named_elements.itervalues())
            remaining = new_element_set - element_set
            element_set = new_element_set

        for (pattern, (element, _)) in self.untyped_elements.iteritems():
            if _is_complex_pattern(pattern.pattern):
                if not checks.is_any(element):
                    element.type = self._convert_complex_type(
                        pattern.pattern, pattern.define_name, element.schema)
            else:
                element.type = self._convert_simple_type(
                    pattern.pattern, pattern.define_name, element.schema)

    def _convert_start(self, start_pattern):
        def convert_root_element(pattern, ns, name, qualified, excpt=None):
            assert name is not None, 'Any is not allowed as top-level element'
            self.added_elements.add(pattern)

            schema = self.all_schemata[ns]
            elem = elements.Element(name, None, None, schema)
            assert pattern not in self.untyped_elements
            self.untyped_elements[pattern] = (elem, qualified)
            schema.elements.append(elem)
            # No need to return anything as we've already
            # done all what we needed.

        def convert_root_elements(pattern):
            if isinstance(pattern, rng_element.RngElement):
                _convert_named_component(pattern, convert_root_element)
            else:
                for p in pattern.patterns:
                    convert_root_elements(p)

        convert_root_elements(start_pattern.pattern)

    def _convert_element(self, elem_pattern):
        def convert_local_element(pattern, ns, name, qualified, excpt=None):
            self.added_elements.add(pattern)
            if name is None and ns is None:
                any_elem = elements.Any([], None)
                assert pattern not in self.untyped_elements
                self.untyped_elements[pattern] = (any_elem, False)
            elif name is None:
                constraint = elements.Any.Name(ns, None)
                any_elem = elements.Any([constraint], None)
                assert pattern not in self.untyped_elements
                self.untyped_elements[pattern] = (any_elem, False)
            else:
                elem_schema = self.all_schemata[ns]
                elem = elements.Element(name, None, None, elem_schema)
                assert pattern not in self.untyped_elements
                self.untyped_elements[pattern] = (elem, qualified)
            # No need to return anything as we don't use it here.

        _convert_named_component(elem_pattern, convert_local_element)

    def _convert_simple_type(self, type_pattern, component_name, schema):
        type_name = self._get_next_name('{}-type'.format(component_name))
        t = elements.SimpleType(type_name, schema)
        schema.simple_types.append(t)

        if isinstance(type_pattern, rng_empty.RngEmpty):
            t.restriction = elements.Restriction(schema)
            t.restriction.base = xsd_types.xsd_builtin_types()['string']
            t.restriction.length = '0'
        elif isinstance(type_pattern, rng_value.RngValue):
            assert type_pattern.value is not None

            t.restriction = elements.Restriction(schema)
            t.restriction.base = type_pattern.type
            t.restriction.enumeration.append(
                elements.EnumerationValue(type_pattern.value, ''))
        elif isinstance(type_pattern, rng_text.RngText):
            return xsd_types.xsd_builtin_types()['string']
        elif isinstance(type_pattern, rng_data.RngData):
            if not type_pattern.params and type_pattern.except_pattern is None:
                schema.simple_types.pop()
                return type_pattern.type

            t.restriction = elements.Restriction(schema)
            t.restriction.base = type_pattern.type
            _set_restriction_params(type_pattern, t.restriction)
            # if type_pattern.except_pattern is not None:
            #     assert False, 'Not implemented'
        elif isinstance(type_pattern, rng_list.RngList):
            self._convert_list_type(t, type_pattern.data_pattern, schema)
        elif isinstance(type_pattern, rng_choice.RngChoicePattern):
            # has_empty = False
            # enum_types = {}

            for p in type_pattern.patterns:
                choice_item_name = self._get_next_name(
                    '{}-choice'.format(type_name))
                t.union.append(
                    self._convert_simple_type(p, choice_item_name, schema))

                # if isinstance(p, rng_empty.RngEmpty):
                #     pass
                #     # has_empty = True
                # elif isinstance(p, rng_oneOrMore.RngOneOrMore):
                #     pass
                # elif isinstance(p, rng_value.RngValue):
                #     type_key = '{}:{}'.format(p.datatypes_uri, p.type.name)
                #     enum_type = enum_types.get(type_key, None)
                #     if enum_type is None:
                #         enum_type_name = \
                #             '{}-choice{}'.format(type_name, len(enum_types))
                #         enum_type = elements.SimpleType(enum_type_name, schema)
                #         enum_type.restriction = elements.Restriction(schema)
                #         enum_type.restriction.base = p.type

                #     enum_type.restriction.enumeration.append(
                #         elements.EnumerationValue(p.value, ''))
                # elif isinstance(p, rng_data.RngData):
                #     t.union.append(p.type)
        elif isinstance(type_pattern, rng_group.RngGroup):
            pass
        elif isinstance(type_pattern, rng_interleave.RngInterleave):
            pass
        elif isinstance(type_pattern, rng_oneOrMore.RngOneOrMore):
            pass

        return t

    def _convert_list_type(self, t, type_pattern, schema):
        item_name = self._get_next_name('{}-list-item'.format(t.name))

        if isinstance(type_pattern, rng_choice.RngChoicePattern):
            item_type = None
            has_empty = False
            multiple = False
            for p in type_pattern.patterns:
                if isinstance(p, rng_empty.RngEmpty):
                    has_empty = True
                elif isinstance(type_pattern, rng_oneOrMore.RngOneOrMore):
                    assert item_type is None
                    multiple = True
                    item_type = self._convert_simple_type(
                        p.patterns[0], item_name, schema)
                else:
                    assert item_type is None
                    item_type = self._convert_simple_type(p, item_name, schema)

            assert item_type is not None
            min_occurs = 0 if has_empty else 1
            max_occurs = base.UNBOUNDED if multiple else 1
            t.listitems.append(
                uses.ListTypeCardinality(item_type, min_occurs, max_occurs))
        elif isinstance(type_pattern, rng_oneOrMore.RngOneOrMore):
            item_type = self._convert_simple_type(
                type_pattern.patterns[0], item_name, schema)

            t.listitems.append(
                uses.ListTypeCardinality(item_type, 1, base.UNBOUNDED))
        elif isinstance(type_pattern, rng_group.RngGroup):
            for p in type_pattern.patterns:
                item_type = self._convert_simple_type(p, item_name, schema)

                t.listitems.append(
                    uses.ListTypeCardinality(item_type, 1, 1))
        else:
            item_type = self._convert_simple_type(
                type_pattern.data_pattern, item_name, schema)

            t.listitems.append(
                uses.ListTypeCardinality(item_type, 0, base.UNBOUNDED))

    def _convert_union_type(self):
        return

    def _convert_complex_type(self, type_pattern, element_name, schema):
        type_name = self._get_next_name('{}-type'.format(element_name))
        t = elements.ComplexType(type_name, schema)
        schema.complex_types.append(t)

        max_occurs = 1
        if isinstance(type_pattern, rng_empty.RngEmpty):
            struct = None
        elif isinstance(type_pattern, rng_oneOrMore.RngOneOrMore):
            assert len(type_pattern.patterns) == 1
            struct = self._convert_type_structure(type_pattern.patterns[0],
                                                  element_name,
                                                  schema)
            max_occurs = base.UNBOUNDED
        else:
            struct = self._convert_type_structure(type_pattern,
                                                  element_name,
                                                  schema)

        if ((checks.is_particle(struct) and
                not checks.is_compositor(struct.term)) or
                checks.is_attribute_use(struct)):
            sequence = elements.Sequence(schema)
            sequence.members.append(struct)
            t.structure = uses.Particle(False, 1, 1, sequence)
        elif checks.is_particle(struct):
            t.structure = struct
        elif struct is None:
            t.structure = None
        else:
            struct.max_occurs = max_occurs
            t.structure = struct

        return t

    def _convert_type_structure(self, type_pattern, element_name, schema):
        def convert_compositor(compositor):
            min_occurs = 1
            max_occurs = 1

            for p in type_pattern.patterns:
                if isinstance(p, rng_empty.RngEmpty):
                    min_occurs = 0
                    continue
                elif isinstance(p, rng_oneOrMore.RngOneOrMore):
                    assert len(p.patterns) == 1
                    max_occurs = base.UNBOUNDED
                    p = p.patterns[0]

                struct = self._convert_type_structure(p, element_name, schema)

                if checks.is_particle(struct):
                    struct.min_occurs = min_occurs
                    struct.max_occurs = max_occurs
                    compositor.members.append(struct)
                elif checks.is_attribute_use(struct):
                    struct.required = min_occurs > 0
                    compositor.members.append(struct)

            if len(compositor.members) == 1:
                result = compositor.members[0]
                if checks.is_particle(result):
                    result.min_occurs *= min_occurs
                    result.max_occurs *= max_occurs
                elif checks.is_attribute_use(result):
                    result.required = result.required or min_occurs > 0
                return result

            return uses.Particle(False, 1, 1, compositor)

        if isinstance(type_pattern, rng_attribute.RngAttribute):
            def convert_attribute(pattern, ns, name, qualified, excpt=None):
                if name is None and ns is None:
                    any_attr = elements.Any([], schema)
                    return uses.AttributeUse(False, None, False, any_attr)
                elif name is None:
                    name_constraint = elements.Any.Name(ns, None)
                    any_attr = elements.Any([name_constraint], schema)
                    return uses.AttributeUse(False, None, False, any_attr)
                else:
                    constraint = base.ValueConstraint(False, None)

                    if checks.is_xml_namespace(ns):
                        return uses.AttributeUse(
                            False, constraint, False,
                            elements.xml_attributes()[name])

                    if ns == '':
                        a_schema = schema
                    else:
                        a_schema = self.all_schemata[ns]
                        qualified = qualified if a_schema == schema else False
                    attr = elements.Attribute(name, None, None, a_schema)
                    attr.type = self._convert_simple_type(
                        pattern.pattern, name, a_schema)
                    return uses.AttributeUse(
                        qualified, constraint, False, attr)

            return _convert_named_component(type_pattern, convert_attribute)
        elif isinstance(type_pattern, rng_element.RngElement):
            (elem, qualified) = self.untyped_elements[type_pattern]
            if checks.is_any(elem):
                elem.schema = schema
            return uses.Particle(qualified, 1, 1, elem)
        elif isinstance(type_pattern, rng_text.RngText):
            return elements.SchemaText(xsd_types.xsd_builtin_types()['string'])
        elif isinstance(type_pattern, rng_data.RngData):
            data_type_name = \
                self._get_next_name('{}-simple-type'.format(element_name))
            return elements.SchemaText(self._convert_simple_type(
                type_pattern, data_type_name, schema))
        elif isinstance(type_pattern, rng_value.RngValue):
            value_type_name = \
                self._get_next_name('{}-simple-type'.format(element_name))
            return elements.SchemaText(self._convert_simple_type(
                type_pattern, value_type_name, schema))
        elif isinstance(type_pattern, rng_choice.RngChoicePattern):
            choice = elements.Choice(schema)
            return convert_compositor(choice)
        elif isinstance(type_pattern, rng_group.RngGroup):
            sequence = elements.Sequence(schema)
            return convert_compositor(sequence)
        elif isinstance(type_pattern, rng_interleave.RngInterleave):
            allp = elements.All(schema)
            return convert_compositor(allp)
        else:
            assert False

    def _get_next_name(self, name):
        if name in self.unique_type_names:
            self.unique_type_counter += 1
            new_name = '{}{}'.format(name, self.unique_type_counter)
            self.unique_type_names.add(new_name)
            return new_name

        self.unique_type_names.add(name)
        return name


def _convert_named_component(elem_or_attr_pattern, convert_func):
    assert (isinstance(elem_or_attr_pattern, rng_element.RngElement) or
            isinstance(elem_or_attr_pattern, rng_attribute.RngAttribute))

    def handle_name_class(name):
        if isinstance(name, rng_name.RngName):
            return convert_func(elem_or_attr_pattern, name.ns,
                                name.name, name.qualified)
        elif isinstance(name, rng_anyName.RngAnyName):
            return convert_func(elem_or_attr_pattern, None, None, None,
                                excpt=name.except_name_class)
        elif isinstance(name, rng_nsName.RngNsName):
            return convert_func(elem_or_attr_pattern, name.ns, None, None,
                                excpt=name.except_name_class)
        else:
            assert False

    return handle_name_class(elem_or_attr_pattern.name)


def _is_complex_pattern(type_pattern):
    def is_complex_pattern_internal(pattern):
        if (isinstance(pattern, rng_choice.RngChoicePattern) or
                isinstance(pattern, rng_group.RngGroup) or
                isinstance(pattern, rng_interleave.RngInterleave) or
                isinstance(pattern, rng_oneOrMore.RngOneOrMore)):
            for p in pattern.patterns:
                if is_complex_pattern_internal(p):
                    return True
        elif (isinstance(pattern, rng_attribute.RngAttribute) or
                isinstance(pattern, rng_element.RngElement)):
            return True

        return False

    if isinstance(type_pattern, rng_empty.RngEmpty):
        return True

    return is_complex_pattern_internal(type_pattern)


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
