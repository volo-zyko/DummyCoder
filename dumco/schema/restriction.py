# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import checks

import prv.enumeration
from prv.resolvers import resolve_simple_type


class Restriction(base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(Restriction, self).__init__(attrs, parent_schema)

        # Name is neccessary when naming STs.
        self.name = None
        self.base = None
        self.enumeration = []
        self.length = None
        self.max_exclusive = None
        self.max_inclusive = None
        self.max_length = None
        self.min_exclusive = None
        self.min_inclusive = None
        self.min_length = None
        self.pattern = None

    @method_once
    def finalize(self, factory):
        base = None
        if self.attr('base') is None:
            for t in self.children:
                assert checks.is_simple_type(t) and base is None, \
                    'Wrong content of Restriction'

                base = t.finalize(factory)
        elif self.base is None:
            base = resolve_simple_type(self.attr('base'), self.schema, factory)
            base.finalize(factory)
        else:
            base = self.base

        self.base = self._merge_base_restriction(base)

        if self.enumeration:
            self.enumeration = [
                (e.value, e.doc) if isinstance(e, prv.enumeration.Enumeration)
                else e for e in self.enumeration]

        return super(Restriction, self).finalize(None)

    def _merge_base_restriction(self, base):
        def merge(attr):
            if not getattr(self, attr):
                value = getattr(base.restriction, attr)
                setattr(self, attr, value)

        if checks.is_restriction_type(base):
            merge('enumeration')
            merge('length')
            merge('max_exclusive')
            merge('max_inclusive')
            merge('max_length')
            merge('min_exclusive')
            merge('min_inclusive')
            merge('min_length')
            merge('pattern')

            base = self._merge_base_restriction(base.restriction.base)

        return base
