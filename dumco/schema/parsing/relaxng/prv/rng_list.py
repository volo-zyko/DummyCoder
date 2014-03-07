# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import rng_base
import rng_choice
import rng_data
import rng_empty
import rng_group
import rng_notAllowed
import rng_oneOrMore
import rng_ref
import rng_value


def rng_list(attrs, parent_element, factory, grammar_path, all_grammars):
    lst = RngList(attrs, parent_element)
    parent_element.children.append(lst)

    return (lst, {
        'choice': rng_choice.rng_choice,
        'data': rng_data.rng_data,
        'empty': rng_empty.rng_empty,
        'externalRef': factory.noop_handler,
        'group': rng_group.rng_group,
        'notAllowed': rng_notAllowed.rng_notAllowed,
        'oneOrMore': rng_oneOrMore.rng_oneOrMore,
        'optional': factory.rng_optional,
        'parentRef': factory.noop_handler,
        'ref': rng_ref.rng_ref,
        'value': rng_value.rng_value,
        'zeroOrMore': factory.rng_zeroOrMore,
    })


class RngList(rng_base.RngBase):
    def __init__(self, attrs, parent_element):
        super(RngList, self).__init__(attrs, parent_element)

        self.data_pattern = None

    @method_once
    def finalize(self, grammar, factory):
        patterns = []
        for c in self.children:
            patterns.append(c)

        assert patterns, 'List element has no patterns'
        if len(patterns) == 1:
            self.data_pattern = patterns[0]
        else:
            self.data_pattern = rng_group.RngGroup({}, self)
            self.data_pattern.children = patterns

        self.data_pattern.finalize(grammar, factory)

        super(RngList, self).finalize(grammar, factory)

    def _dump_internals(self, fhandle, indent):
        fhandle.write('>\n')
        self.data_pattern.dump(fhandle, indent)
        return rng_base.RngBase._CLOSING_TAG
