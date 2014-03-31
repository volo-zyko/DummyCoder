# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base


def rng_text(attrs, parent_element, factory, grammar_path, all_grammars):
    text = RngText(attrs)
    parent_element.children.append(text)

    return (text, {})


class RngText(rng_base.RngBase):
    def _dump_internals(self, fhandle, indent):
        return rng_base.RngBase._CLOSING_EMPTY_TAG
