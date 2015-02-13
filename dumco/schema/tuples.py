# Distributed under the GPLv2 License; see accompanying file COPYING.

import checks


class _ComponentProxy(object):
    # This class ensures that containing_dict contains parent in
    # the right place no matter how we change its sub-objects.
    def __init__(self, component, parent, containing_dict):
        object.__setattr__(self, '_component', component)
        object.__setattr__(self, '_parent', parent)
        object.__setattr__(self, '_containing_dict', containing_dict)

    def __setattr__(self, name, value):
        del self._containing_dict[self._parent]
        setattr(self._component, name, value)
        self._containing_dict[self._parent] = self._parent._component

    def __getattr__(self, name):
        return _ComponentProxy(getattr(self._component, name),
                               self._parent, self._containing_dict)


class HashableModel(object):
    def __init__(self, component, containing_dict):
        object.__setattr__(self, '_component', component)
        object.__setattr__(self, '_containing_dict', containing_dict)

    def __eq__(self, other):
        return self._get_as_tuple() == other._get_as_tuple()

    def __hash__(self):
        return hash(self._get_as_tuple())

    def __setattr__(self, name, value):
        del self._containing_dict[self]
        setattr(self._component, name, value)
        self._containing_dict[self] = self._component

    def __getattr__(self, name):
        return _ComponentProxy(getattr(self._component, name),
                               self, self._containing_dict)


class HashableAttributeUse(HashableModel):
    def _get_as_tuple(self):
        return get_attribute_use_tuple(self._component)


class HashableComplexType(HashableModel):
    def _get_as_tuple(self):
        return get_complex_type_tuple(self._component)


class HashableParticle(HashableModel):
    def _get_as_tuple(self):
        return get_structure_tuple(self._component)


class HashableSimpleType(HashableModel):
    def _get_as_tuple(self):
        return get_primitive_type_tuple(self._component)


def get_attribute_tuple(a):
    if checks.is_attribute(a):
        return (a.schema, a.name, a.qualified, a.constraint, a.type)
    elif checks.is_any(a):
        return ('anyAttr', a.schema, a.constraint)
    else:
        assert False, 'Unknown attribute'


def get_attribute_use_tuple(u):
    assert checks.is_attribute_use(u)
    return (u.constraint, u.required, get_attribute_tuple(u.attribute))


def get_complex_type_tuple(ct):
    assert checks.is_complex_type(ct)
    if ct.structure is None:
        return ('ct', ct.schema, None)
    return ('ct', ct.schema, get_structure_tuple(ct.structure))


def get_element_tuple(e):
    assert checks.is_element(e)
    return (e.schema, e.name, e.qualified, e.constraint, e.type)


def get_element_particle_tuple(p):
    assert checks.is_particle(p)
    return (p.min_occurs, p.max_occurs, get_element_tuple(p.term))


def get_particle_tuple(p):
    assert checks.is_particle(p)
    return (p.min_occurs, p.max_occurs, get_term_tuple(p.term))


def get_primitive_type_tuple(t):
    if checks.is_native_type(t):
        return (t.uri, t.name)
    elif checks.is_restriction_type(t):
        r = t.restriction
        return (t.schema, r.fraction_digits, r.length, r.max_exclusive,
                r.max_inclusive, r.max_length, r.min_exclusive,
                r.min_inclusive, r.min_length, r.total_digits,
                r.white_space, tuple([p for p in r.patterns]),
                tuple(sorted([e.value for e in r.enumerations])),
                get_primitive_type_tuple(r.base))
    elif checks.is_list_type(t):
        l = t.listitems
        return (t.schema, tuple([(i.min_occurs, i.max_occurs,
                                  get_primitive_type_tuple(i.type))
                                 for i in l]))
    elif checks.is_union_type(t):
        u = t.union
        return (t.schema, tuple([get_primitive_type_tuple(m) for m in u]))
    else:
        assert False, 'Unknown primitive type'


def get_structure_tuple(s):
    if checks.is_particle(s):
        if checks.is_element(s.term):
            return get_element_particle_tuple(s)
        else:
            return get_particle_tuple(s)
    elif checks.is_attribute_use(s):
        return get_attribute_use_tuple(s)
    elif checks.is_text(s):
        return ('txt', get_primitive_type_tuple(s.type))
    else:
        assert False, 'Unknown structure element'


def get_term_tuple(t):
    if checks.is_sequence(t):
        return ('seq', tuple([get_structure_tuple(m) for m in t.members]))
    elif checks.is_choice(t):
        return ('chc', tuple(sorted([get_structure_tuple(m)
                                     for m in t.members])))
    elif checks.is_interleave(t):
        return ('ilv', tuple(sorted([get_structure_tuple(m)
                                     for m in t.members])))
    elif checks.is_any(t):
        return ('anyElem', t.schema, t.constraint)
    else:
        assert False, 'Unknown compositor'
