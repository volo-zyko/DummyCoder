# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.checks
import dumco.schema.elements as elements
import dumco.schema.xsd_types as xsd_types

import rng_anyName
import rng_attribute
import rng_choice
import rng_data
import rng_element
import rng_empty
import rng_grammar
import rng_group
# import rng_interleave
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

    def convert(self, grammar):
        assert isinstance(grammar, rng_grammar.RngGrammar)

        added_elements = set()
        self._convert_start(grammar.start, added_elements)

        for e in grammar.elements:
            if e not in added_elements:
                self._convert_element(e)

    def _convert_start(self, start, added_elements):
        def add_element(pattern, ns, name, excpt=None):
            assert name is not None, 'Any is not allowed as top-level element'

            schema = self.all_schemata[ns]
            element = elements.Element(name, None, None, schema)
            schema.elements.append(element)

            added_elements.add(pattern)
            name = '{}-type'.format(pattern.define_name)
            element.type = self._convert_type(pattern, name, schema)

        def create_top_level_elements(pattern):
            if isinstance(pattern, rng_element.RngElement):
                _create_named_component(pattern, add_element)
            else:
                for p in pattern.patterns:
                    create_top_level_elements(p)

        create_top_level_elements(start.pattern)

    def _convert_element(self, element):
        def add_element(pattern, ns, name, excpt=None):
            if name is None and ns is None:
                pass
            elif name is None:
                pass
            else:
                schema = self.all_schemata[ns]
                elem = elements.Element(name, None, None, schema)
                schema.elements.append(elem)

                element.type = self._convert_type(
                    pattern, pattern.define_name, schema)

        _create_named_component(element, add_element)

    def _convert_simple_type(self, pattern, name, schema):
        if isinstance(pattern, rng_empty.RngEmpty):
            t = elements.SimpleType(name, schema)
            schema.simple_types.append(t)

            t.restriction.base = xsd_types.xsd_builtin_types()['string']
            t.restriction.length = '0'

            return t
        elif isinstance(pattern, rng_text.RngText):
            return xsd_types.xsd_builtin_types()['string']
        elif isinstance(pattern, rng_data.RngData):
            if not pattern.params and pattern.except_pattern is None:
                return pattern.type

            t = elements.SimpleType(name, schema)
            schema.simple_types.append(t)

            t.restriction.base = pattern.type
            _set_restriction_params(pattern, t.restriction)
            if pattern.except_pattern is not None:
                assert False, 'Not implemented'

            return t
        elif isinstance(pattern, rng_value.RngValue):
            assert pattern.value is not None

            return elements.EnumerationValue(pattern.value, '')
        elif isinstance(pattern, rng_list.RngList):
            t = elements.SimpleType(name, schema)
            schema.simple_types.append(t)

            t.listitem = self._convert_simple_type(pattern.data_pattern,
                                                   None, schema)

            return t
        elif isinstance(pattern, rng_choice.RngChoicePattern):
            pass

    def _convert_type(self, pattern, element_name, element_schema):
        if isinstance(pattern, rng_empty.RngEmpty):
            t = elements.ComplexType('{}-type'.format(element_name),
                                     element_schema)
            element_schema.complex_types.append(t)
            return t
        # elif isinstance(pattern, rng_element.RngElement):
        #     return
        elif isinstance(pattern, rng_attribute.RngAttribute):
            return
        elif isinstance(pattern, rng_choice.RngChoicePattern):
            return
        elif isinstance(pattern, rng_oneOrMore.RngOneOrMore):
            return
        elif isinstance(pattern, rng_group.RngGroup):
            return
        # elif isinstance(pattern, rng_interleave.RngInterleave):
        #     return
        else:
            t = elements.ComplexType('{}-type'.format(element_name),
                                     element_schema)
            return t


def _create_named_component(elem_or_attr, add_to_model):
    assert (isinstance(elem_or_attr, rng_element.RngElement) or
            isinstance(elem_or_attr, rng_attribute.RngAttribute))

    def handle_name_class(name):
        if isinstance(name, rng_name.RngName):
            add_to_model(elem_or_attr, name.ns, name.name)
        elif isinstance(name, rng_anyName.RngAnyName):
            add_to_model(elem_or_attr, None, None,
                         excpt=name.except_name_class)
        elif isinstance(name, rng_nsName.RngNsName):
            add_to_model(elem_or_attr, name.ns, None,
                         excpt=name.except_name_class)
        elif isinstance(name, rng_choice.RngChoiceName):
            for n in name.name_classes:
                handle_name_class(n)

    handle_name_class(elem_or_attr.name)


def _set_restriction_params(data, restriction):
    if dumco.schema.checks.is_xsd_namespace(data.datatypes_uri):
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
