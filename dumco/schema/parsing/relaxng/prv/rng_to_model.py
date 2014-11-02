# Distributed under the GPLv2 License; see accompanying file COPYING.

import copy
import operator

from dumco.utils.decorators import method_once

import dumco.schema.base as base
import dumco.schema.checks as checks
import dumco.schema.elements as elements
import dumco.schema.enums as enums
import dumco.schema.namer as namer
import dumco.schema.tuples as tuples
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

        self.unique_simple_types = {}
        self.unique_complex_types = {}
        self.unique_attribute_uses = {}
        self.unique_element_uses = {}

    def convert(self, grammar):
        assert isinstance(grammar, rng_grammar.RngGrammar)

        added_elements = set()
        self._convert_start(grammar.start, added_elements)

        for e in sorted(grammar.named_elements.itervalues(),
                        key=lambda e: e.define_name):
            if e not in added_elements:
                self._convert_element(e)

        for (pattern, (element, _)) in self.untyped_elements.iteritems():
            if checks.is_any(element) or element.type is not None:
                # Simple content types we convert when we convert elements.
                continue

            # Type is not defined only for complex types.
            element.type = \
                self._convert_complex_type(pattern.pattern, element.schema)

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
                t = type_pattern.type
            else:
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

            def fold_listitems(acc, x):
                if (acc and tuples.HashableSimpleType(x.type, None) ==
                        tuples.HashableSimpleType(acc[-1].type, None)):
                    min_occurs = uses.min_occurs_op(acc[-1].min_occurs,
                                                    x.min_occurs, operator.add)
                    max_occurs = uses.max_occurs_op(acc[-1].max_occurs,
                                                    x.max_occurs, operator.add)
                    acc[-1] = uses.ListTypeCardinality(acc[-1].type,
                                                       min_occurs, max_occurs)
                    return acc

                return acc + [x]

            t.listitems = reduce(fold_listitems, t.listitems, [])
            assert len(t.listitems) > 0
        elif isinstance(type_pattern, rng_choice.RngChoicePattern):
            t = elements.SimpleType(None, schema)
            self._convert_union_type(type_pattern, t, schema)

            def fold_members(acc, x):
                found = any([tuples.HashableSimpleType(x, None) ==
                             tuples.HashableSimpleType(y, None) for y in acc])
                return acc if found else acc + [x]

            t.union = reduce(fold_members, t.union, [])

            assert len(t.union) > 0
            if len(t.union) == 1:
                t = t.union[0]
        else:
            assert False, 'Unexpected pattern for simple type'

        return _get_unique_entity(
            self.unique_simple_types,
            tuples.HashableSimpleType(t, self.unique_simple_types))

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
            (_, struct) = self._convert_type_structure(p, schema)
        else:
            (_, struct) = self._convert_type_structure(type_pattern, schema)

        if ((checks.is_particle(struct) and checks.is_element(struct.term)) or
                checks.is_attribute_use(struct) or checks.is_text(struct)):
            # Struct is either single element or attribute or text,
            # thus we have to wrap struct in a compositor.
            sequence = elements.Sequence(schema)
            sequence.members.append(struct)
            t.structure = uses.Particle(False, 1, max_occurs, sequence)
        elif struct is None:
            t.structure = None
        elif checks.is_particle(struct):
            max_occurs = \
                uses.max_occurs_op(struct.max_occurs, max_occurs, operator.mul)

            if len(struct.term.members) == 1:
                first_part = struct.term.members[0]
                max_occurs = uses.max_occurs_op(first_part.max_occurs,
                                                max_occurs, operator.mul)
                struct = first_part

            struct.max_occurs = max_occurs
            t.structure = struct
        else:
            assert False, 'Unknown complex type structure'

        return _get_unique_entity(
            self.unique_complex_types,
            tuples.HashableComplexType(t, self.unique_complex_types))

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

                (assign_occurs, struct) = \
                    self._convert_type_structure(p, schema)

                if (checks.is_particle(struct) and
                        type(compositor) == type(struct.term) and
                        min_occurs == 1 and max_occurs == 1):
                    compositor.members.extend(struct.term.members)
                elif checks.is_particle(struct):
                    if assign_occurs:
                        struct.min_occurs = min_occurs
                        struct.max_occurs = max_occurs
                    if (checks.is_element(struct.term) and
                            struct.term.type is not None):
                        struct = self._merge_element_enum_types(struct)
                    compositor.members.append(struct)
                elif checks.is_attribute_use(struct):
                    if assign_occurs and checks.is_attribute(struct.attribute):
                        struct.required = min_occurs > 0
                        struct = self._merge_attribute_enum_types(struct)
                    compositor.members.append(struct)
                elif checks.is_text(struct):
                    compositor.members.append(struct)

            def fold_particles(acc, x):
                if (acc and checks.is_particle(x) and
                        checks.is_particle(acc[-1]) and
                        tuples.HashableParticle(x, None) ==
                        tuples.HashableParticle(acc[-1], None)):
                    acc[-1].min_occurs = uses.min_occurs_op(acc[-1].min_occurs,
                                                            x.min_occurs,
                                                            operator.add)
                    acc[-1].max_occurs = uses.max_occurs_op(acc[-1].max_occurs,
                                                            x.max_occurs,
                                                            operator.add)
                    return acc

                return acc + [x]

            compositor.members = reduce(fold_particles, compositor.members, [])

            assert len(compositor.members) != 0

            if len(compositor.members) != 1:
                return (True, uses.Particle(False, 1, 1, compositor))

            struct = compositor.members[0]
            if checks.is_particle(struct):
                struct.min_occurs = uses.min_occurs_op(struct.min_occurs,
                                                       min_occurs, operator.mul)
                struct.max_occurs = uses.max_occurs_op(struct.max_occurs,
                                                       max_occurs, operator.mul)
            elif checks.is_attribute_use(struct):
                struct.required = struct.required or min_occurs > 0

            return (False, struct)

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
                        return (True, elements.xml_attributes()[name])

                    self.namer.learn_naming(name, namer.NAME_HINT_ATTR)

                    if ns == '':
                        attr_schema = schema
                    else:
                        attr_schema = self.all_schemata[ns]

                    attr = elements.Attribute(name, attr_schema)
                    attr.type = \
                        self._convert_simple_type(pattern.pattern, attr_schema)

                return (True,
                        uses.AttributeUse(None, False, qualified, False, attr))

            return _convert_named_component(type_pattern, convert_attribute)
        elif isinstance(type_pattern, rng_element.RngElement):
            (elem, qualified) = self.untyped_elements[type_pattern]
            if checks.is_any(elem):
                elem.schema = schema
            if not _is_complex_pattern(type_pattern.pattern):
                elem.type = self._convert_simple_type(type_pattern.pattern,
                                                      elem.schema)
            return (True, uses.Particle(qualified, 1, 1, elem))
        elif isinstance(type_pattern, rng_text.RngText):
            return (False,
                    uses.SchemaText(xsd_types.xsd_builtin_types()['string']))
        elif (isinstance(type_pattern, rng_data.RngData) or
                isinstance(type_pattern, rng_value.RngValue)):
            t = self._convert_simple_type(type_pattern, schema)
            return (False, uses.SchemaText(t))
        elif isinstance(type_pattern, rng_choice.RngChoicePattern):
            if _is_complex_pattern(type_pattern):
                choice = elements.Choice(schema)
                return convert_compositor(choice)
            else:
                t = self._convert_simple_type(type_pattern, schema)
                return (False, uses.SchemaText(t))
        elif isinstance(type_pattern, rng_group.RngGroup):
            sequence = elements.Sequence(schema)
            return convert_compositor(sequence)
        elif isinstance(type_pattern, rng_interleave.RngInterleave):
            interleave = elements.Interleave(schema)
            return convert_compositor(interleave)
        else:
            assert False

    def _merge_attribute_enum_types(self, use):
        if checks.is_enumeration_type(use.attribute.type):
            hashable_use = tuples.HashableAttributeUse(
                use, self.unique_attribute_uses)
            (type_merge_candidates, type_referring_entities) = \
                self._collect_enum_type_users(hashable_use)

            if type_merge_candidates:
                old_type = type_merge_candidates[0].attribute.type

                if type_referring_entities:
                    new_type = copy.copy(old_type)
                    new_type.restriction = copy.copy(old_type.restriction)
                    new_type.restriction.enumeration = \
                        copy.copy(old_type.restriction.enumeration)

                    new_type = _get_unique_entity(
                        self.unique_simple_types,
                        tuples.HashableSimpleType(new_type,
                                                  self.unique_simple_types))

                    for entity in type_referring_entities:
                        entity.type = new_type

                use.attribute.type = self._merge_enum_types(
                    use.attribute.type, old_type)

                for entity in type_merge_candidates:
                    entity.type = use.attribute.type

        return _get_unique_entity(
            self.unique_attribute_uses,
            tuples.HashableAttributeUse(use, self.unique_attribute_uses))

    def _merge_element_enum_types(self, part):
        if checks.is_enumeration_type(part.term.type):
            hashable_part = tuples.HashableParticle(
                part, self.unique_element_uses)
            (type_merge_candidates, type_referring_entities) = \
                self._collect_enum_type_users(hashable_part)

            if type_merge_candidates:
                old_type = type_merge_candidates[0].term.type

                if type_referring_entities:
                    new_type = copy.copy(old_type)
                    new_type.restriction = copy.copy(old_type.restriction)
                    new_type.restriction.enumeration = \
                        copy.copy(old_type.restriction.enumeration)

                    new_type = _get_unique_entity(
                        self.unique_simple_types,
                        tuples.HashableSimpleType(new_type,
                                                  self.unique_simple_types))

                    for entity in type_referring_entities:
                        entity.type = new_type

                part.term.type = self._merge_enum_types(
                    part.term.type, old_type)

                for entity in type_merge_candidates:
                    entity.type = part.term.type

        return _get_unique_entity(
            self.unique_element_uses,
            tuples.HashableParticle(part, self.unique_element_uses))

    def _collect_enum_type_users(self, hashable_use):
        # There can be many, say attributes, with same name/ns but with
        # different constraints (fixed/default, optional/required, etc) and
        # which still have enumeration type. However, if logic for enumeration
        # merging works fine then all candidates found here should have the
        # same type.
        type_merge_candidates = []
        # There can be both attributes and elements that use the same type.
        type_referring_entities = []
        # There is no intersection between entities in the lists above.

        for u in self.unique_attribute_uses:
            if u == hashable_use:
                if (u.attribute.type != hashable_use.attribute.type and
                        checks.is_enumeration_type(u.attribute.type)):
                    type_merge_candidates.append(u)
            elif (checks.is_attribute_use(hashable_use._component) and
                    u.attribute.type == hashable_use.attribute.type):
                type_referring_entities.append(u.attribute)

        for u in self.unique_element_uses:
            if u == hashable_use:
                if (u.term.type != hashable_use.term.type and
                        checks.is_enumeration_type(u.term.type)):
                    type_merge_candidates.append(u)
            elif (checks.is_particle(hashable_use._component) and
                    u.term.type == hashable_use.term.type):
                type_referring_entities.append(u.term)

        assert (not type_merge_candidates or
                (type_merge_candidates and
                 all([type_merge_candidates[0].type == u.type
                      for u in type_merge_candidates[1:]])))

        return (type_merge_candidates, type_referring_entities)

    def _merge_enum_types(self, changing_enum_type, redundant_enum_type):
        assert changing_enum_type != redundant_enum_type

        enums = {x.value: x for x in changing_enum_type.restriction.enumeration}
        enums.update(
            {x.value: x for x in redundant_enum_type.restriction.enumeration})
        changing_enum_type.restriction.enumeration = list(enums.itervalues())

        # Remove redundant_enum_type if there are no referring entities.
        self.unique_simple_types = filter(
            lambda t: t == redundant_enum_type, self.unique_simple_types)

        return _get_unique_entity(
            self.unique_simple_types,
            tuples.HashableSimpleType(changing_enum_type,
                                      self.unique_simple_types))


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


def _get_unique_entity(unique_entities, new_entity):
    return unique_entities.setdefault(new_entity, new_entity._component)
