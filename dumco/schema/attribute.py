# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import checks

from prv.resolvers import resolve_attribute, resolve_simple_type


class Attribute(base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(Attribute, self).__init__(attrs, parent_schema)

        self.name = self.attr('name')
        self.type = None
        self.qualified = (self.attr('form') == 'qualified' or
            (self.attr('form') != 'unqualified') and
             self.schema is not None and
             self.schema.attr('attributeFormDefault') == 'qualified')

    @method_once
    def finalize(self, factory):
        ret = self
        if self.attr('ref') is not None:
            ret = resolve_attribute(self.attr('ref'), self.schema, factory)
        elif self.attr('type') is not None:
            self.type = resolve_simple_type(self.attr('type'),
                                            self.schema, factory)
        else:
            self.type = factory.simple_urtype
            for t in self.children:
                assert checks.is_simple_type(t), \
                    'Attribute can contain only its type'
                self.type = t

        super(Attribute, self).finalize(None)
        return ret
