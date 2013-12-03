# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base


def rng_text(attrs, parent_element, factory, grammar_path, all_grammars):
    text = RngText(attrs, parent_element, grammar_path)
    parent_element.children.append(text)

    return (text, {})


class RngText(rng_base.RngBase):
    def __init__(self, attrs, parent_element, grammar_path):
        super(RngText, self).__init__(attrs, parent_element)
