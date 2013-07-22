# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.base

import extension_cc
import restriction_cc


class ComplexContent(dumco.schema.base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(ComplexContent, self).__init__(attrs, parent_schema)

        self.mixed = (None if self.attr('mixed') is None
                           else (self.attr('mixed') == 'true' or
                                 self.attr('mixed') == '1'))
        self.term = None
        self.attributes = []

    @method_once
    def finalize(self, factory):
        for c in self.children:
            assert ((isinstance(c, extension_cc.ComplexExtension) or
                     isinstance(c, restriction_cc.ComplexRestriction)) and
                    self.term is None), 'Wrong content of ComplexContent'

            c.finalize(factory)
            self.term = c.term
            self.attributes = c.attributes

        return super(ComplexContent, self).finalize(None)
