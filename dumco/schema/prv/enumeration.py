# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.base


class Enumeration(dumco.schema.base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(Enumeration, self).__init__(attrs, parent_schema)

        self.value = self.attr('value')
