# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import rng_anyName
import rng_base
import rng_choice
import rng_name
import rng_nsName
import rng_utils


def rng_except(attrs, parent_element, factory, grammar_path, all_grammars):
    excpt = RngExcept(attrs, parent_element)
    parent_element.children.append(excpt)

    return (excpt, {
        'anyName': rng_anyName.rng_anyName,
        'choice': rng_choice.rng_choice,
        'name': rng_name.rng_name,
        'nsName': rng_nsName.rng_nsName,
    })


class RngExcept(rng_base.RngBase):
    def __init__(self, attrs, parent_element):
        super(RngExcept, self).__init__(attrs, parent_element)

        self.name_classes = []

    @method_once
    def finalize(self, grammar, all_schemata, factory):
        for c in self.children:
            assert rng_utils.is_name_class(c), \
                'Wrong content of except element'

            c.finalize(grammar, all_schemata, factory)
            self.name_classes.append(c)

        super(RngExcept, self).finalize(grammar, all_schemata, factory)

    def _dump_internals(self, fhandle, indent):
        assert self.name_classes, 'Empty except element'

        fhandle.write('>\n')
        for n in self.name_classes:
            n.dump(fhandle, indent)

        return rng_base.RngBase._CLOSING_TAG
