# Distributed under the GPLv2 License; see accompanying file COPYING.

import collections

from dumco.utils.decorators import method_once

import base
import checks
import namer


class AttributeUse(object):
    def __init__(self, default, fixed, qualified, required, attribute):
        # constraint = ValueConstraint.
        self.constraint = base.ValueConstraint(fixed, default)
        # qualified = boolean.
        self.qualified = qualified
        # required = boolean.
        self.required = required
        # attribute = Attribute/Any.
        self.attribute = attribute

    def append_doc(self, doc):
        self.attribute.append_doc(doc)


# Utility class necessary for better traversing dumco model.
ChildComponent = collections.namedtuple('ChildComponent',
                                        ['parents', 'component'])


ListTypeCardinality = collections.namedtuple(
    'ListTypeCardinality', ['type', 'min_occurs', 'max_occurs'])


class Particle(object):
    def __init__(self, qualified, min_occurs, max_occurs, term):
        assert min_occurs <= max_occurs

        # qualified = boolean.
        self.qualified = qualified
        # min_occurs = integer.
        self.min_occurs = min_occurs
        # max_occurs = integer.
        self.max_occurs = max_occurs
        # term = Element/Sequence/Choice/All/Any.
        self.term = term
        self.name = None

    def append_doc(self, doc):
        self.term.append_doc(doc)

    def traverse(self, flatten=True, parents=None):
        assert checks.is_compositor(self.term)

        if not flatten:
            yield ChildComponent(parents, self)

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
                                            parents=[self] + parents):
                        yield child
                else:
                    yield ChildComponent([self] + parents, x)

    @method_once
    def nameit(self, parents, factory, names):
        namer.forge_name(self, parents, factory, names)

        assert checks.is_compositor(self.term), \
            'Trying to name non-compositor'

        for p in self.term.members:
            if not checks.is_particle(p):
                continue

            if checks.is_compositor(p.term):
                p.nameit(parents + [self], factory, names)
                assert p.name is not None, 'Name cannot be None'


class SchemaText(object):
    # In case of mixed content in complex type SchemaText represents
    # constraints for text content. It is used along with Particles and
    # AttributeUses.
    def __init__(self, simple_type):
        self.type = simple_type
