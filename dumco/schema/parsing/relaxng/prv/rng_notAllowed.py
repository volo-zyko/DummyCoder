# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base


def rng_notAllowed(attrs, parent_element, factory, grammar_path, all_grammars):
    not_allowed = RngNotAllowed(attrs, parent_element)
    parent_element.children.append(not_allowed)

    return (not_allowed, {})


class RngNotAllowed(rng_base.RngBase):
    def __init__(self, attrs, parent_element):
        super(RngNotAllowed, self).__init__(attrs, parent_element)

    def _dump_internals(self, fhandle, indent):
        return rng_base.RngBase._CLOSING_EMPTY_TAG
