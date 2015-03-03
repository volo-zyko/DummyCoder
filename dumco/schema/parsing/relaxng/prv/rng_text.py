# Distributed under the GPLv2 License; see accompanying file COPYING.

import base
import utils


def rng_text(attrs, parent_element, factory, grammar_path, all_grammars):
    parent_element.children.append(RngText())

    return (parent_element.children[-1], {})


class RngText(base.RngBase):
    def dump(self, context):
        with utils.RngTagGuard('text', context):
            pass
