# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.base
import dumco.schema.checks

from resolvers import resolve_simple_type
import utils


class List(dumco.schema.base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(List, self).__init__(attrs, parent_schema)

        # Name is neccessary when naming STs.
        self.name = None
        self.itemtype = None

    @method_once
    def finalize(self, factory):
        if self.attr('itemType') is None:
            for t in self.children:
                assert (dumco.schema.checks.is_simple_type(t) and
                        self.itemtype is None), \
                    'Wrong content of List'

                self.itemtype = t
        else:
            self.itemtype = \
                resolve_simple_type(self.attr('itemType'), self.schema, factory)
        self.itemtype.finalize(factory)

        return super(List, self).finalize(None)
