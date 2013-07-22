# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import checks

import prv.group


class Sequence(base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(Sequence, self).__init__(attrs, parent_schema)

        self.particles = []

    @method_once
    def finalize(self, factory):
        for c in self.children:
            assert (checks.is_compositor(c.element) or
                    checks.is_element(c.element) or checks.is_any(c.element) or
                    isinstance(c.element, prv.group.Group)), \
                'Wrong content of Sequence'

            c.element = c.element.finalize(factory)
            if isinstance(c.element, prv.group.Group):
                c.element = c.element.body
            self.particles.append(c)

        return super(Sequence, self).finalize(None)
