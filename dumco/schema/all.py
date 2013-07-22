# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import checks


class All(base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(All, self).__init__(attrs, parent_schema)

        self.particles = []

    @method_once
    def finalize(self, factory):
        for c in self.children:
            assert checks.is_element(c.element), \
                'Only Element is allowed in All'

            c.element = c.element.finalize(factory)
            self.particles.append(c)

        return super(All, self).finalize(None)
