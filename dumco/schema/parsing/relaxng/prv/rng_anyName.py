# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base
import rng_except


def rng_anyName(attrs, parent_element, factory, grammar_path, all_grammars):
    any_name = RngAnyName(attrs, parent_element, grammar_path)
    parent_element.children.append(any_name)

    return (any_name, {
        'except': rng_except.rng_except,
    })


class RngAnyName(rng_base.RngBase):
    def __init__(self, attrs, parent_element, grammar_path):
        super(RngAnyName, self).__init__(attrs, parent_element)
