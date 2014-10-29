# Distributed under the GPLv2 License; see accompanying file COPYING.

import checks


def equal_attributes(a1, a2, check_type=True):
    if type(a1) != type(a2) or not checks.is_attribute(a1):
        return False

    return (a1.schema == a2.schema and a1.name == a2.name and
            (not check_type or equal_primitive_types(a1.type, a2.type)))


def equal_attribute_uses(u1, u2):
    if type(u1) != type(u2) or not checks.is_attribute_use(u1):
        return False

    return (u1.constraint == u2.constraint and
            u1.qualified == u2.qualified and
            u1.required == u2.required and
            equal_attributes(u1.attribute, u2.attribute))


def equal_complex_types(ct1, ct2):
    if (type(ct1) != type(ct2) or
            not checks.is_complex_type(ct1) or
            ct1.schema != ct2.schema):
        return False

    if ct1.structure is None or ct2.structure is None:
        return ct1.structure == ct2.structure

    return equal_particles(ct1.structure, ct2.structure)


def equal_elements(e1, e2, check_type=True):
    if type(e1) != type(e2) or not checks.is_element(e1):
        return False

    return (e1.schema == e2.schema and e1.name == e2.name and
            e1.constraint == e2.constraint and
            (not check_type or
             (checks.is_complex_type(e1.type) and
              checks.is_complex_type(e2.type) and
              equal_particles(e1.type.structure, e2.type.structure)) or
             (checks.is_primitive_type(e1.type) and
              checks.is_primitive_type(e2.type) and
              equal_primitive_types(e1.type, e2.type))))


def equal_particles(p1, p2):
    if type(p1) != type(p2) or not checks.is_particle(p1):
        return False

    def equal_choices(c1, c2):
        if (type(c1) != type(c2) or not checks.is_choice(c1) or
                len(c1.members) != len(c2.members)):
            return False

        return _equal_lists(c1.members, c2.members, equal_particles)

    def equal_interleaves(i1, i2):
        if (type(i1) != type(i2) or not checks.is_choice(i1) or
                len(i1.members) != len(i2.members)):
            return False

        return _equal_lists(i1.members, i2.members, equal_particles)

    def equal_sequences(s1, s2):
        if (type(s1) != type(s2) or not checks.is_choice(s1) or
                len(s1.members) != len(s2.members)):
            return False

        return all([equal_particles(m1, m2)
                    for (m1, m2) in zip(s1.members, s2.members)])

    return (p1.qualified == p2.qualified and
            p1.min_occurs == p2.min_occurs and
            p1.max_occurs == p2.max_occurs and
            (equal_elements(p1.term, p2.term) or
             equal_sequences(p1.term, p2.term) or
             equal_choices(p1.term, p2.term) or
             equal_interleaves(p1.term, p2.term)))


def equal_primitive_types(st1, st2):
    if (type(st1) != type(st2) or
            not checks.is_primitive_type(st1) or
            st1.schema != st2.schema):
        return False

    if checks.is_native_type(st1):
        return st1 == st2
    elif checks.is_restriction_type(st1) or checks.is_restriction_type(st2):
        def equal_restrictions(r1, r2):
            if r1 is None or r2 is None:
                return False

            if r1.base != r2.base:
                # Base is always native type and they are generated once for
                # the whole program run, so it is ok to compare references.
                return False
            if not _equal_lists(r1.enumeration, r2.enumeration,
                                lambda e1, e2: e1.value == e2.value):
                return False
            if r1.fraction_digits != r2.fraction_digits:
                return False
            if r1.length != r2.length:
                return False
            if r1.max_exclusive != r2.max_exclusive:
                return False
            if r1.max_inclusive != r2.max_inclusive:
                return False
            if r1.max_length != r2.max_length:
                return False
            if r1.min_exclusive != r2.min_exclusive:
                return False
            if r1.min_inclusive != r2.min_inclusive:
                return False
            if r1.min_length != r2.min_length:
                return False
            if r1.pattern != r2.pattern:
                return False
            if r1.total_digits != r2.total_digits:
                return False
            if r1.white_space != r2.white_space:
                return False

            return True

        return equal_restrictions(st1.restriction, st2.restriction)
    elif checks.is_list_type(st1) or checks.is_list_type(st2):
        if not len(st1.listitems) == len(st2.listitems):
            return False

        def equal_list_items(i1, i2):
            return (i1.min_occurs == i2.min_occurs and
                    i1.max_occurs == i2.max_occurs and
                    equal_primitive_types(i1.type, i2.type))

        for (li1, li2) in zip(st1.listitems, st2.listitems):
            if not equal_list_items(li1, li2):
                return False

        return True
    elif _equal_lists(st1.union, st2.union, equal_primitive_types):
        # Checking permutations of types in unions might seem wrong but
        # if types are totally different say, enum and numeric, it doesn't
        # matter in which order we match input string to them and if types
        # are similar, like token and enum, then more specific type (enum
        # in this case) must be first in list otherwise it's not usable
        # at all.
        return True

    return False


def _equal_lists(list1, list2, items_equal):
    if len(list1) != len(list2):
        return False

    for i in list1:
        list2 = filter(lambda x: not items_equal(i, x), list2)

    return len(list2) == 0
