# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import rng_base
import rng_except


def rng_anyName(attrs, parent_element, factory, grammar_path, all_grammars):
    any_name = RngAnyName(attrs)
    parent_element.children.append(any_name)

    return (any_name, {
        'except': rng_except.rng_except,
    })


class RngAnyName(rng_base.RngBase):
    def __init__(self, attrs):
        super(RngAnyName, self).__init__(attrs)

        self.except_name_class = None

    @method_once
    def finalize(self, grammar, factory):
        for c in self.children:
            assert (isinstance(c, rng_except.RngExceptName) and
                    self.except_name_class is None), \
                'Wrong content of anyName element'

            c.finalize(grammar, factory)
            self.except_name_class = c

        super(RngAnyName, self).finalize(grammar, factory)

    def _dump_internals(self, fhandle, indent):
        if self.except_name_class is None:
            return rng_base.RngBase._CLOSING_EMPTY_TAG
        else:
            fhandle.write('>\n')
            self.except_name_class.dump(fhandle, indent)
            return rng_base.RngBase._CLOSING_TAG
