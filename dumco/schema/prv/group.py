# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.base
import dumco.schema.checks

from resolvers import resolve_group


class Group(dumco.schema.base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(Group, self).__init__(attrs, parent_schema)

        self.name = self.attr('name')
        self.body = None

    @method_once
    def finalize(self, factory):
        ret = self
        if self.attr('ref') is not None:
            g = resolve_group(self.attr('ref'), self.schema)
            ret = g.finalize(factory)
        else:
            for c in self.children:
                assert (dumco.schema.checks.is_compositor(c.element) and
                        self.body is None), 'Wrong content of Group'

                c.element = c.element.finalize(factory)
                self.body = c.element

        super(Group, self).finalize(None)
        return ret
