# Distributed under the GPLv2 License; see accompanying file COPYING.

import collections

import base
import checks


class AttributeUse(object):
    def __init__(self, default, fixed, required, attribute):
        self._docs = []
        # constraint = ValueConstraint.
        self.constraint = base.ValueConstraint(default, fixed)
        # required = boolean.
        self.required = required
        # attribute = Attribute/Any.
        self.attribute = attribute

    def append_doc(self, doc):
        text = doc.strip()
        if text != '':
            self._docs.append(text)


# Utility class necessary for better traversing dumco model.
ChildComponent = collections.namedtuple('ChildComponent',
                                        ['parents', 'component'])


ListTypeCardinality = collections.namedtuple(
    'ListTypeCardinality', ['type', 'min_occurs', 'max_occurs'])


class Particle(object):
    def __init__(self, min_occurs, max_occurs, term):
        assert min_occurs <= max_occurs

        self._docs = []
        # min_occurs = integer.
        self.min_occurs = min_occurs
        # max_occurs = integer.
        self.max_occurs = max_occurs
        # term = Element/Sequence/Choice/All/Any.
        self.term = term

    def append_doc(self, doc):
        text = doc.strip()
        if text != '':
            self._docs.append(text)

    def traverse(self, flatten=True, parents=None):
        assert checks.is_compositor(self.term)

        for x in self.term.members:
            assert ((checks.is_particle(x) and
                     (checks.is_terminal(x.term) or
                      checks.is_compositor(x.term)))
                    or
                    (checks.is_attribute_use(x) and
                     (checks.is_attribute(x.attribute) or
                      checks.is_any(x.attribute)))
                    or
                    checks.is_text(x)), \
                'Unknown member in compositor'

            if flatten:
                if checks.is_particle(x) and checks.is_compositor(x.term):
                    for m in x.traverse():
                        yield m
                else:
                    yield x
            else:
                if checks.is_particle(x) and checks.is_compositor(x.term):
                    for child in x.traverse(flatten=False,
                                            parents=parents + [self]):
                        yield child
                else:
                    yield ChildComponent(parents + [self], x)


class SchemaText(object):
    # In case of mixed content in complex type SchemaText represents
    # constraints for text content. It is used along with Particles and
    # AttributeUses.
    def __init__(self, simple_type):
        self.type = simple_type


def min_occurs_op(occurs1, occurs2, op):
    res = op(occurs1, occurs2)
    assert res < base.UNBOUNDED
    return res


def max_occurs_op(occurs1, occurs2, op):
    res = op(occurs1, occurs2)
    if res > base.UNBOUNDED:
        return base.UNBOUNDED
    return res


def attribute_key(attr_use, referencing_schema):
    if checks.is_any(attr_use.attribute):
        return ('', '')
    elif attr_use.attribute.schema != referencing_schema:
        return (attr_use.attribute.schema.prefix, attr_use.attribute.name)
    return ('', attr_use.attribute.name)
