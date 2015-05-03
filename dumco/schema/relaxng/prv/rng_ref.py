# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base


def rng_ref(attrs, parent_element, builder, grammar_path, all_grammars):
    name = builder.get_attribute(attrs, 'name').strip()
    parent_element.children.append(RngRef(name))

    return (parent_element.children[-1], {})


class RngRef(base.RngBase):
    def __init__(self, name):
        super(RngRef, self).__init__()

        self.name = name
        self.ref_pattern = None

    @method_once
    def finalize(self, grammar, builder):
        define = grammar.get_define(self.name)

        self.ref_pattern = define.pattern
        while (len(self.ref_pattern) == 1 and
                isinstance(self.ref_pattern[0], RngRef)):
            self.ref_pattern = self.ref_pattern[0].ref_pattern

        assert self.ref_pattern is not None, 'Reference is malformed'

        super(RngRef, self).finalize(grammar, builder)
        return self.ref_pattern
