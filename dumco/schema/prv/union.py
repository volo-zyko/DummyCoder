# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.base
import dumco.schema.checks

from resolvers import resolve_simple_type
import utils


class Union(dumco.schema.base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(Union, self).__init__(attrs, parent_schema)

        # Name is neccessary when naming STs.
        self.name = None
        self.membertypes = []

    @method_once
    def finalize(self, factory):
        if self.attr('memberTypes') is not None:
            for t in self.attr('memberTypes').split():
                membertype = resolve_simple_type(t, self.schema, factory)
                membertype.finalize(factory)
                self._merge_unions(t, membertype)

        for t in self.children:
            assert dumco.schema.checks.is_simple_type(t), \
                'Wrong content of Union'

            t.finalize(factory)
            self._merge_unions(t.name, t)

        # Remove duplicates.
        self.membertypes = reduce(
            lambda accum, m: accum if m in accum else accum + [m],
            self.membertypes, [])

        assert self.membertypes, 'No member types in union'

        return super(Union, self).finalize(None)

    def _merge_unions(self, name, member):
        if dumco.schema.checks.is_union_type(member):
            for (t, membertype) in member.union:
                self._merge_unions(t, membertype)
        else:
            self.membertypes.append((name, member))
