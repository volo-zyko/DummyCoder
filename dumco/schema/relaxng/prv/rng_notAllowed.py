# Distributed under the GPLv2 License; see accompanying file COPYING.

import base
import utils


def rng_notAllowed(attrs, parent_element, builder, grammar_path, all_grammars):
    parent_element.children.append(RngNotAllowed())

    return (parent_element.children[-1], {})


class RngNotAllowed(base.RngBase):
    def dump(self, context):
        with utils.RngTagGuard('notAllowed', context):
            pass
