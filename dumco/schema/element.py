# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import checks

from prv.resolvers import resolve_element, resolve_type


class Element(base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(Element, self).__init__(attrs, parent_schema)

        self.name = self.attr('name')
        self.type = None
        self.qualified = (self.attr('form') == 'qualified' or
            (self.attr('form') != 'unqualified') and
             self.schema is not None and
             self.schema.attr('elementFormDefault') == 'qualified')

    @method_once
    def finalize(self, factory):
        ret = self
        if self.attr('ref') is not None:
            ret = resolve_element(self.attr('ref'), self.schema)
        elif self.attr('type') is not None:
            self.type = resolve_type(self.attr('type'),
                                     self.schema, factory)
        elif self.attr('substitutionGroup') is not None:
            elem = resolve_element(self.attr('substitutionGroup'), self.schema)
            elem = elem.finalize(factory)
            self.type = elem.type
        else:
            self.type = factory.complex_urtype
            for t in self.children:
                assert (checks.is_complex_type(t) or
                        checks.is_simple_type(t)), \
                    'Element can contain only its type'
                self.type = t

        super(Element, self).finalize(None)
        return ret
