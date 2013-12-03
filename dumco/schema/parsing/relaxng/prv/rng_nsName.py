# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base
import rng_except


def rng_nsName(attrs, parent_element, factory, grammar_path, all_grammars):
    ns_name = RngNsName(attrs, parent_element, grammar_path, factory)
    parent_element.children.append(ns_name)

    return (ns_name, {
        'except': rng_except.rng_except,
    })


class RngNsName(rng_base.RngBase):
    def __init__(self, attrs, parent_element, grammar_path, factory):
        super(RngNsName, self).__init__(attrs, parent_element)

        self.ns = factory.get_ns()
