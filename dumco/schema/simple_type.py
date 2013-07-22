# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import checks
import restriction

import prv.list
import prv.union
import prv.utils


class SimpleType(base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(SimpleType, self).__init__(attrs, parent_schema)

        self.name = self.attr('name')
        self.restriction = None
        self.listitem = None
        self.union = []

    @staticmethod
    def urtype(factory):
        urtype = SimpleType({}, None)
        urtype.name = 'anySimpleType'

        restr = restriction.Restriction({}, None)
        restr.base = factory.complex_urtype
        urtype.restriction = restr

        urtype.finalize(factory)

        return urtype

    @method_once
    def finalize(self, factory):
        for c in self.children:
            assert (isinstance(c, restriction.Restriction) or
                    isinstance(c, prv.list.List) or
                    isinstance(c, prv.union.Union)), \
                'Wrong content of SimpleType'

            if isinstance(c, restriction.Restriction):
                c.finalize(factory)
                self.restriction = c
            elif isinstance(c, prv.list.List):
                c.finalize(factory)
                self.listitem = c.itemtype
            elif isinstance(c, prv.union.Union):
                c.finalize(factory)
                self.union = c.membertypes

        assert ((self.restriction is not None and
                 self.listitem is None and self.union == []) or
                (self.listitem is not None and
                 self.restriction is None and self.union == []) or
                (self.union != [] and
                 self.listitem is None and self.restriction is None)), \
            'SimpleType must be any of restriction, list, union'

        return super(SimpleType, self).finalize(None)

    @method_once
    def nameit(self, parents, factory, names):
        prv.utils.forge_name(self, parents, factory, names)
