# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base
import rng_group
import rng_interleave
import rng_oneOrMore


def rng_empty(attrs, parent_element, factory, grammar_path, all_grammars):
    if (isinstance(parent_element, rng_group.RngGroup) or
        isinstance(parent_element, rng_interleave.RngInterleave) or
        isinstance(parent_element, rng_oneOrMore.RngOneOrMore)):
        return (parent_element, {})

    empty = RngEmpty(attrs, parent_element)
    parent_element.children.append(empty)

    return (empty, {})


class RngEmpty(rng_base.RngBase):
    def __init__(self, attrs, parent_element):
        super(RngEmpty, self).__init__(attrs, parent_element)

    def _dump_internals(self, fhandle, indent):
        return rng_base.RngBase._CLOSING_EMPTY_TAG
