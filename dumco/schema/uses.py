# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import checks
import namer


class Particle(object):
    def __init__(self, qualified, min_occurs, max_occurs, term):
        self.qualified = qualified
        assert min_occurs <= max_occurs
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs
        self.term = term
        self.name = None

    def append_doc(self, doc):
        self.term.append_doc(doc)

    @method_once
    def nameit(self, parents, factory, names):
        namer.forge_name(self, parents, factory, names)

        assert checks.is_compositor(self.term), \
            'Trying to name non-compositor'

        for p in self.term.particles:
            if checks.is_compositor(p.term):
                p.nameit(parents + [self], factory, names)
                assert p.name is not None, 'Name cannot be None'


class AttributeUse(object):
    def __init__(self, qualified, constraint, required, attribute):
        self.qualified = qualified
        self.constraint = constraint
        self.required = required
        self.attribute = attribute

    def append_doc(self, doc):
        self.attribute.append_doc(doc)
