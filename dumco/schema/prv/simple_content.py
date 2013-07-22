# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.base

import extension_sc
import restriction_sc


class SimpleContent(dumco.schema.base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(SimpleContent, self).__init__(attrs, parent_schema)

        self.base = None
        self.attributes = []

    @method_once
    def finalize(self, factory):
        for c in self.children:
            assert ((isinstance(c, extension_sc.SimpleExtension) or
                     isinstance(c, restriction_sc.SimpleRestriction)) and
                    self.base is None), 'Wrong content of SimpleContent'

            c.finalize(factory)

            self.base = c.base
            self.attributes = c.attributes

        return super(SimpleContent, self).finalize(None)
