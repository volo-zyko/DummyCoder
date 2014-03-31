# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import rng_base


def rng_ref(attrs, parent_element, factory, grammar_path, all_grammars):
    ref = RngRef(attrs)
    parent_element.children.append(ref)

    return (ref, {})


class RngRef(rng_base.RngBase):
    def __init__(self, attrs):
        super(RngRef, self).__init__(attrs)

        self.ref_pattern = None

    def get_ref_pattern(self, grammar):
        if self.ref_pattern is None:
            name = self.attr('name').strip()

            define = grammar.get_define(name)
            define.prefinalize(grammar)

            self.ref_pattern = define.pattern

        assert self.ref_pattern is not None, 'Reference is malformed'

        return self.ref_pattern

    @method_once
    def finalize(self, grammar, factory):
        # Make self.ref_pattern valid.
        self.get_ref_pattern(grammar)

        self.ref_pattern.finalize(grammar, factory)

        return super(RngRef, self).finalize(grammar, factory)
