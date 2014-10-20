# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.base as base
import dumco.schema.checks as checks
import dumco.schema.elements as elements
import dumco.schema.enums as enums
import dumco.schema.namer as namer
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
        self.namer = factory.namer

        self.untyped_elements = {}

    def convert(self, grammar):
        assert isinstance(grammar, rng_grammar.RngGrammar)

        added_elements = set()
        self._convert_start(grammar.start, added_elements)

        for e in sorted(grammar.named_elements.itervalues(),
                        key=lambda e: e.define_name):
            if e not in added_elements:
                self._convert_element(e)

        for (pattern, (element, _)) in self.untyped_elements.iteritems():
            if _is_complex_pattern(pattern.pattern):
                if checks.is_any(element):
                    continue

                element.type = \
                    self._convert_complex_type(pattern.pattern, element.schema)
            else:
                element.type = \
                    self._convert_simple_type(pattern.pattern, element.schema)

        def traverse_complex_type(ct, parent, vcts):
            if ct in vcts:
                return

            ct.name = self.namer.name_ct(None, ct.schema.target_ns, parent)
            ct.schema.complex_types.append(ct)
            vcts.add(ct)

            for child in enums.enum_flat(ct):
                if checks.is_attribute_use(child):
                    if checks.is_any(child.attribute):
                        continue
                    traverse_simple_type(child.attribute.type, child.attribute)
                elif checks.is_particle(child):
                    if checks.is_any(child.term):
                        continue

                    if checks.is_complex_type(child.term.type):
                        traverse_complex_type(child.term.type, child.term, vcts)
                    elif checks.is_complex_type(child.term.type):
                        traverse_simple_type(child.term.type, child.term)
                elif checks.is_text(child):
                    traverse_simple_type(child.type, child)

        def traverse_simple_type(st, parent):
            if (checks.is_native_type(st) or
                    st.schema is None and st.name is not None):
                return

            st.name = self.namer.name_st(None, st.schema.target_ns, parent)
            st.schema.simple_types.append(st)

            if checks.is_list_type(st):
                for item in st.listitems:
                    traverse_simple_type(item.type, st)
            elif checks.is_union_type(st):
                for member in st.union:
                    traverse_simple_type(member, st)

        # Now we can name types.
        visited_cts = set()
        for schema in self.all_schemata.itervalues():
            for elem in schema.elements:
                if checks.is_complex_type(elem.type):
                    traverse_complex_type(elem.type, elem, visited_cts)
                elif checks.is_simple_type(elem.type):
                    traverse_simple_type(elem.type, elem)

        for schema in self.all_schemata.itervalues():
            schema.simple_types.sort(key=lambda s: s.name)
            schema.complex_types.sort(key=lambda c: c.name)

    def _convert_start(self, start_pattern, added_elements):
        def convert_root_element(pattern, ns, name, qualified, excpt=None):
            assert name is not None, 'Any is not allowed as top-level element'
            assert pattern not in self.untyped_elements

            added_elements.add(pattern)

            schema = self.all_schemata[ns]
            elem = elements.Element(name, None, False, schema)
            schema.elements.append(elem)

            self.namer.learn_naming(name, namer.NAME_HINT_ELEM)
            self.untyped_elements[pattern] = (elem, qualified)
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
            assert pattern not in self.untyped_elements
            if name is None and ns is None:
                any_elem = elements.Any([], None)
                self.untyped_elements[pattern] = (any_elem, False)
            elif name is None:
                constraint = elements.Any.Name(ns, None)
                any_elem = elements.Any([constraint], None)
                self.untyped_elements[pattern] = (any_elem, False)
            else:
                elem_schema = self.all_schemata[ns]
                elem = elements.Element(name, None, False, elem_schema)

                self.namer.learn_naming(name, namer.NAME_HINT_ELEM)
                self.untyped_elements[pattern] = (elem, qualified)
            # No need to return anything as we don't use it here.

        _convert_named_component(elem_pattern, convert_local_element)

    def _convert_simple_type(self, type_pattern, schema):
        if isinstance(type_pattern, rng_empty.RngEmpty):
            t = self._forge_empty_simple_type(schema)
        elif isinstance(type_pattern, rng_value.RngValue):
            assert type_pattern.value is not None

            t = elements.SimpleType(None, schema)
            t.restriction = elements.Restriction(schema)
            t.restriction.base = type_pattern.type
            t.restriction.enumeration.append(
                elements.EnumerationValue(type_pattern.value, ''))
        elif isinstance(type_pattern, rng_text.RngText):
            return xsd_types.xsd_builtin_types()['string']
        elif isinstance(type_pattern, rng_data.RngData):
            if not type_pattern.params and type_pattern.except_pattern is None:
                return type_pattern.type

            t = elements.SimpleType(None, schema)
            t.restriction = elements.Restriction(schema)
            t.restriction.base = type_pattern.type
            if not _set_restriction_params(type_pattern, t.restriction):
                t = type_pattern.type
            # if type_pattern.except_pattern is not None:
            #     assert False, 'Not implemented'
        elif isinstance(type_pattern, rng_list.RngList):
            t = elements.SimpleType(None, schema)
            self._convert_list_type(type_pattern.data_pattern, t, schema)
        elif isinstance(type_pattern, rng_choice.RngChoicePattern):
            t = elements.SimpleType(None, schema)
            self._convert_union_type(type_pattern, t, schema)

            if len(t.union) == 1:
                t = t.union[0]
        else:
            assert False, 'Unexpected pattern for simple type'

        return t

    @method_once
    def _forge_empty_simple_type(self, schema):
        empty_type = elements.SimpleType(None, schema)
        empty_type.restriction = elements.Restriction(schema)
        empty_type.restriction.base = xsd_types.xsd_builtin_types()['string']
        empty_type.restriction.length = '0'
        return empty_type

    def _convert_list_type(self, type_pattern, parent_type, schema):
        def append_list_item(item_type, min_occurs, max_occurs):
            parent_type.listitems.append(
                uses.ListTypeCardinality(item_type, min_occurs, max_occurs))

        if isinstance(type_pattern, rng_choice.RngChoicePattern):
            item_type = None
            has_empty = False
            multiple = False

            for p in type_pattern.patterns:
                if isinstance(p, rng_empty.RngEmpty):
                    has_empty = True
                elif isinstance(p, rng_oneOrMore.RngOneOrMore):
                    assert item_type is None

                    multiple = True
                    item_type = self._convert_simple_type(p.patterns[0], schema)
                else:
                    assert item_type is None

                    item_type = self._convert_simple_type(p, schema)

            assert item_type is not None

            min_occurs = 0 if has_empty else 1
            max_occurs = base.UNBOUNDED if multiple else 1

            append_list_item(item_type, min_occurs, max_occurs)
        elif isinstance(type_pattern, rng_oneOrMore.RngOneOrMore):
            p = type_pattern.patterns[0]
            item_type = self._convert_simple_type(p, schema)

            append_list_item(item_type, 1, base.UNBOUNDED)
        elif isinstance(type_pattern, rng_group.RngGroup):
            for p in type_pattern.patterns:
                item_type = self._convert_simple_type(p, schema)

                append_list_item(item_type, 1, 1)
        else:
            p = type_pattern.data_pattern
            item_type = self._convert_simple_type(p, schema)

            append_list_item(item_type, 0, base.UNBOUNDED)

    def _convert_union_type(self, type_pattern, parent_type, schema):
        enum_types = {}
        for p in type_pattern.patterns:
            if isinstance(p, rng_value.RngValue):
                enum_type = enum_types.get((p.datatypes_uri, p.type))
                if enum_type is None:
                    enum_type = elements.SimpleType(None, schema)
                    enum_type.restriction = elements.Restriction(schema)
                    enum_type.restriction.base = p.type

                    enum_types[(p.datatypes_uri, p.type)] = enum_type

                    parent_type.union.append(enum_type)

                enum_type.restriction.enumeration.append(
                    elements.EnumerationValue(p.value, ''))
            elif (isinstance(p, rng_empty.RngEmpty) or
                    isinstance(p, rng_data.RngData) or
                    isinstance(p, rng_list.RngList) or
                    isinstance(p, rng_text.RngText) or
                    isinstance(p, rng_choice.RngChoicePattern)):
                parent_type.union.append(
                    self._convert_simple_type(p, schema))
            elif isinstance(p, rng_oneOrMore.RngOneOrMore):
                pass
            else:
                assert False, 'Unexpected pattern for simple type'

    def _convert_complex_type(self, type_pattern, schema):
        t = elements.ComplexType(None, schema)

        max_occurs = 1
        if isinstance(type_pattern, rng_empty.RngEmpty):
            struct = None
        elif isinstance(type_pattern, rng_oneOrMore.RngOneOrMore):
            assert len(type_pattern.patterns) == 1

            max_occurs = base.UNBOUNDED

            p = type_pattern.patterns[0]
            struct = self._convert_type_structure(p, schema)
        else:
            struct = self._convert_type_structure(type_pattern, schema)

        if ((checks.is_particle(struct) and checks.is_element(struct.term)) or
                checks.is_attribute_use(struct) or checks.is_text(struct)):
            # Struct is either single element or attribute or text,
            # thus we have to wrap struct in a compositor.
            sequence = elements.Sequence(schema)
            sequence.members.append(struct)
            t.structure = uses.Particle(False, 1, 1, sequence)
        elif struct is None:
            t.structure = None
        elif checks.is_particle(struct):
            struct.max_occurs = \
                _update_max_occurs(struct.max_occurs, max_occurs)
            t.structure = struct
        else:
            assert False, 'Unknown complex type structure'

        return t

    def _convert_type_structure(self, type_pattern, schema):
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

                struct = self._convert_type_structure(p, schema)

                if checks.is_particle(struct):
                    struct.min_occurs = min_occurs
                    struct.max_occurs = max_occurs
                    compositor.members.append(struct)
                elif checks.is_attribute_use(struct):
                    struct.required = min_occurs > 0
                    compositor.members.append(struct)

            assert len(compositor.members) != 0

            if len(compositor.members) != 1:
                return uses.Particle(False, 1, 1, compositor)

            result = compositor.members[0]
            if checks.is_particle(result):
                result.min_occurs *= min_occurs
                result.max_occurs = \
                    _update_max_occurs(result.max_occurs, max_occurs)
            elif checks.is_attribute_use(result):
                result.required = result.required or min_occurs > 0

            return result

        if isinstance(type_pattern, rng_attribute.RngAttribute):
            def convert_attribute(pattern, ns, name, qualified, excpt=None):
                if name is None and ns is None:
                    attr = elements.Any([], schema)
                    qualified = False
                elif name is None:
                    name_constraint = elements.Any.Name(ns, None)
                    attr = elements.Any([name_constraint], schema)
                    qualified = False
                else:
                    if checks.is_xml_namespace(ns):
                        return elements.xml_attributes()[name]

                    self.namer.learn_naming(name, namer.NAME_HINT_ATTR)

                    if ns == '':
                        attr_schema = schema
                    else:
                        attr_schema = self.all_schemata[ns]
                    qualified = qualified if attr_schema == schema else False

                    attr = elements.Attribute(name, attr_schema)
                    attr.type = \
                        self._convert_simple_type(pattern.pattern, attr_schema)

                return uses.AttributeUse(None, False, qualified, False, attr)

            return _convert_named_component(type_pattern, convert_attribute)
        elif isinstance(type_pattern, rng_element.RngElement):
            (elem, qualified) = self.untyped_elements[type_pattern]
            if checks.is_any(elem):
                elem.schema = schema
            return uses.Particle(qualified, 1, 1, elem)
        elif isinstance(type_pattern, rng_text.RngText):
            return uses.SchemaText(xsd_types.xsd_builtin_types()['string'])
        elif (isinstance(type_pattern, rng_data.RngData) or
                isinstance(type_pattern, rng_value.RngValue)):
            t = self._convert_simple_type(type_pattern, schema)
            return uses.SchemaText(t)
        elif isinstance(type_pattern, rng_choice.RngChoicePattern):
            if _is_complex_pattern(type_pattern):
                choice = elements.Choice(schema)
                return convert_compositor(choice)
            else:
                t = self._convert_simple_type(type_pattern, schema)
                return uses.SchemaText(t)
        elif isinstance(type_pattern, rng_group.RngGroup):
            sequence = elements.Sequence(schema)
            return convert_compositor(sequence)
        elif isinstance(type_pattern, rng_interleave.RngInterleave):
            interleave = elements.Interleave(schema)
            return convert_compositor(interleave)
        else:
            assert False


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
    if not checks.is_xsd_namespace(data.datatypes_uri):
        return False

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

    return bool(data.params)


def _update_max_occurs(old, new):
    if old * new > base.UNBOUNDED:
        return base.UNBOUNDED
    return old * new
