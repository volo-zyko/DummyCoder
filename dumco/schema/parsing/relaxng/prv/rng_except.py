# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_anyName
import rng_base
import rng_choice
import rng_name
import rng_nsName


def rng_except(attrs, parent_element, factory, grammar_path, all_grammars):
    excpt = RngExcept(attrs, parent_element, grammar_path)
    parent_element.children.append(excpt)

    return (excpt, {
        'anyName': rng_anyName.rng_anyName,
        'choice': rng_choice.rng_choice,
        'name': rng_name.rng_name,
        'nsName': rng_nsName.rng_nsName,
    })


class RngExcept(rng_base.RngBase):
    def __init__(self, attrs, parent_element, grammar_path):
        super(RngExcept, self).__init__(attrs, parent_element)
