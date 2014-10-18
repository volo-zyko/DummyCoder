# Distributed under the GPLv2 License; see accompanying file COPYING.

import itertools

import checks


def equal_attribute_uses(u1, u2):
    def equal_attributes(a1, a2):
        return (checks.is_attribute(a1) and
                checks.is_attribute(a2) and
                a1.schema == a2.schema and a1.name == a2.name and
                equal_simple_types(a1.type, a2.type))

    return (checks.is_attribute_use(u1) and
            checks.is_attribute_use(u2) and
            u1.constraint == u2.constraint and
            u1.qualified == u2.qualified and
            u1.required == u2.required and
            equal_attributes(u1.attribute, u2.attribute))


def equal_complex_types(ct1, ct2):
    # No need to call parent's equal_content() since types must not
    # necessarily belong to one schema.
    if ct1.structure is None and ct2.structure is None:
        return True

    return equal_particles(ct1.structure, ct2.structure)


def equal_particles(p1, p2):
    def equal_elements(e1, e2):
        return e1.schema == e2.schema and e1.constraint == e2.constraint

    return (p1.qualified == p2.qualified and
            p1.min_occurs == p2.min_occurs and
            p1.max_occurs == p2.max_occurs and
            equal_terms(p1.term, p2.term))


def equal_simple_types(st1, st2):
    def equal_restrictions(r1, r2):
        def equal_enums(e1, e2):
            return e1.value == e2.value

        if r1 is None or r2 is None:
            return False
        elif not equal_simple_types(r1.base, r2.base):
            return False
        elif not _equal_permutations(
                r1.enumeration, r2.enumeration, equal_enums):
            return False
        elif r1.fraction_digits != r2.fraction_digits:
            return False
        elif r1.length != r2.length:
            return False
        elif r1.max_exclusive != r2.max_exclusive:
            return False
        elif r1.max_inclusive != r2.max_inclusive:
            return False
        elif r1.max_length != r2.max_length:
            return False
        elif r1.min_exclusive != r2.min_exclusive:
            return False
        elif r1.min_inclusive != r2.min_inclusive:
            return False
        elif r1.min_length != r2.min_length:
            return False
        elif r1.pattern != r2.pattern:
            return False
        elif r1.total_digits != r2.total_digits:
            return False
        elif r1.white_space != r2.white_space:
            return False

        return True

    def equal_union_members(m1, m2):
        return equal_simple_types(m1, m2)

    def equal_list_items(i1, i2):
        return (i1.min_occurs == i2.min_occurs and
                i1.max_occurs == i2.max_occurs and
                equal_simple_types(i1.type, i2.type))

    # No need to call parent's equal_content() since types must not
    # necessarily belong to one schema.
    if equal_restrictions(st1.restriction, st2.restriction):
        return True
    elif len(st1.listitems) == len(st2.listitems):
        for (li1, li2) in zip(st1.listitems, st2.listitems):
            if not equal_list_items(li1, li2):
                return False
        return True
    elif _equal_permutations(st1.union, st2.union, equal_union_members):
        return True

    return False


def equal_terms(t1, t2):
    def equal_choices(c1, c2):
        if (not checks.is_choice(c2) or
                not checks.is_choice(c2) or
                len(c1.members) != len(c2.members)):
            return False

        return True

    def equal_interleaves(i1, i2):
        if (not checks.is_interleave(i1) or
                not checks.is_interleave(i2) or
                len(i1.members) != len(i2.members)):
            return False

        return True

    def equal_sequences(s1, s2):
        if (not checks.is_sequence(s1) or
                not checks.is_sequence(s2) or
                len(s1.members) != len(s2.members)):
            return False

        for (m1, m2) in zip(s1.members):
            if not equal_particles(m1, m2):
                return False

        return True

    return True


def _equal_permutations(list1, list2, items_equal):
    if len(list1) != len(list2):
        return False

    # The first permutation is equal to list2.
    for permutation in itertools.permutation(list2):
        if all([items_equal(x, y) for (x, y) in zip(list1, permutation)]):
            return True

    return False
