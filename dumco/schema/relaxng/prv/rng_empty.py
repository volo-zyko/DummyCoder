# Distributed under the GPLv2 License; see accompanying file COPYING.

import base
import utils


def rng_empty(attrs, parent_element, builder, grammar_path, all_grammars):
    parent_element.children.append(RngEmpty())

    return (parent_element.children[-1], {})


class RngEmpty(base.RngBase):
    def dump(self, context):
        with utils.RngTagGuard('empty', context):
            pass
