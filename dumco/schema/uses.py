# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import checks

import prv.utils


class Particle(object):
    def __init__(self, attrs, element, factory):
        self.min_occurs = 1
        self.max_occurs = 1
        self.element = element
        self.name = None

        self._set_multiplicity(attrs, factory)

    @method_once
    def nameit(self, parents, factory, names):
        prv.utils.forge_name(self, parents, factory, names)

        assert checks.is_compositor(self.element), \
            'Trying to name non-compositor'

        for p in self.element.particles:
            if checks.is_compositor(p.element):
                p.nameit(parents + [self], factory, names)
                assert p.name is not None, 'Name cannot be None'

    def _set_multiplicity(self, attrs, factory):
        try:
            min_occurs = factory.get_attribute(attrs, 'minOccurs')
            self.min_occurs = int(min_occurs)
        except LookupError:
            pass

        try:
            max_occurs = factory.get_attribute(attrs, 'maxOccurs')
            self.max_occurs = (base.UNBOUNDED if max_occurs == 'unbounded'
                               else int(max_occurs))
        except LookupError:
            pass

        assert self.min_occurs <= self.max_occurs


class AttributeUse(object):
    def __init__(self, attrs, attribute, factory):
        try:
            self.default = factory.get_attribute(attrs, 'default')
        except LookupError:
            self.default = None
        try:
            self.required = factory.get_attribute(attrs, 'use') == 'required'
        except LookupError:
            self.required = None
        self.attribute = attribute
