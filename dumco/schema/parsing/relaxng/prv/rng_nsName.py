# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import rng_base
import rng_except


def rng_nsName(attrs, parent_element, factory, grammar_path, all_grammars):
    ns_name = RngNsName(attrs, parent_element, factory)
    parent_element.children.append(ns_name)

    return (ns_name, {
        'except': rng_except.rng_except,
    })


class RngNsName(rng_base.RngBase):
    def __init__(self, attrs, parent_element, factory):
        super(RngNsName, self).__init__(attrs, parent_element)

        self.ns = factory.get_ns()
        self.except_name_class = None

    @method_once
    def finalize(self, grammar, all_schemata, factory):
        for c in self.children:
            assert (isinstance(c, rng_except.RngExceptName) and
                    self.except_name_class is None), \
                'Wrong content of nsName element'

            c.finalize(grammar, all_schemata, factory)
            self.except_name_class = c

        super(RngNsName, self).finalize(grammar, all_schemata, factory)

    def _dump_internals(self, fhandle, indent):
        if self.except_name_class is None:
            return rng_base.RngBase._CLOSING_EMPTY_TAG
        else:
            fhandle.write(' ns="{}">\n'.format(self.ns))
            self.except_name_class.dump(fhandle, indent)
            return rng_base.RngBase._CLOSING_TAG
