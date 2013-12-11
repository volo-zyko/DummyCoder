# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import rng_base


def rng_ref(attrs, parent_element, factory, grammar_path, all_grammars):
    ref = RngRef(attrs, parent_element)
    parent_element.children.append(ref)

    return (ref, {})


class RngRef(rng_base.RngBase):
    def __init__(self, attrs, parent_element):
        super(RngRef, self).__init__(attrs, parent_element)

        self.element = None

    def get_element(self, grammar):
        if self.element is None:
            name = self.attr('name').strip()

            define = grammar.get_define(name)
            define.prefinalize(grammar)

            self.element = define.pattern

        assert self.element is not None, 'Reference is malformed'

        return self.element

    @method_once
    def finalize(self, grammar, all_schemata, factory):
        # Make self.element valid.
        self.get_element(grammar)

        self.element.finalize(grammar, all_schemata, factory)

        super(RngRef, self).finalize(grammar, all_schemata, factory)
