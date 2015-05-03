# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import rng_choice
import rng_data
import rng_empty
import rng_group
import rng_notAllowed
import rng_oneOrMore
import rng_ref
import rng_value
import utils


def rng_list(attrs, parent_element, builder, grammar_path, all_grammars):
    parent_element.children.append(RngList())

    return (parent_element.children[-1], {
        'choice': rng_choice.rng_choice,
        'data': rng_data.rng_data,
        'empty': rng_empty.rng_empty,
        'externalRef': builder.noop_handler,
        'group': rng_group.rng_group,
        'notAllowed': rng_notAllowed.rng_notAllowed,
        'oneOrMore': rng_oneOrMore.rng_oneOrMore,
        'optional': builder.rng_optional,
        'parentRef': builder.noop_handler,
        'ref': rng_ref.rng_ref,
        'value': rng_value.rng_value,
        'zeroOrMore': builder.rng_zeroOrMore,
    })


class RngList(base.RngBase):
    def __init__(self, ):
        super(RngList, self).__init__()

        self.data_pattern = None

    @method_once
    def finalize(self, grammar, builder):
        patterns = []
        for c in self.children:
            patterns.append(c)

        assert patterns, 'List element has no patterns'
        if len(patterns) == 1:
            self.data_pattern = patterns[0]
        else:
            self.data_pattern = rng_group.RngGroup()
            self.data_pattern.children = patterns

        self.data_pattern.finalize(grammar, builder)

        return super(RngList, self).finalize(grammar, builder)

    def dump(self, context):
        with utils.RngTagGuard('list', context):
            self.data_pattern.dump(context)
