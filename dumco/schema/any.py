# Distributed under the GPLv2 License; see accompanying file COPYING.

import base


class Any(base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(Any, self).__init__(attrs, parent_schema)

        self.namespace = '##any'

        if self.attr('namespace') is not None:
            value = self.attr('namespace').strip()
            if value == '##any' or value == '##other':
                self.namespace = value
            else:
                self.namespace = value.split()
