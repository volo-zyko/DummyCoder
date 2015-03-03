# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import rng_except
import utils


def rng_nsName(attrs, parent_element, factory, grammar_path, all_grammars):
    parent_element.children.append(RngNsName(factory.get_ns()))

    return (parent_element.children[-1], {
        'except': rng_except.rng_except,
    })


class RngNsName(base.RngBase):
    def __init__(self, ns):
        super(RngNsName, self).__init__()

        self.ns = ns
        self.except_name_class = None

    @method_once
    def finalize(self, grammar, factory):
        for c in self.children:
            assert (isinstance(c, rng_except.RngExceptName) and
                    self.except_name_class is None), \
                'Wrong content of nsName element'

            c.finalize(grammar, factory)
            self.except_name_class = c

        super(RngNsName, self).finalize(grammar, factory)

    def dump(self, context):
        with utils.RngTagGuard('nsName', context):
            context.add_attribute('ns', self.ns)

            if self.except_name_class is not None:
                self.except_name_class.dump(context)
