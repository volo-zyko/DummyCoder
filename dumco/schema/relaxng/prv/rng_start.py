# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import rng_attribute
import rng_choice
import rng_data
import rng_element
import rng_empty
import rng_grammar
import rng_group
import rng_interleave
import rng_list
import rng_notAllowed
import rng_oneOrMore
import rng_ref
import rng_text
import rng_value
import utils


def rng_start(attrs, parent_element, builder, grammar_path, all_grammars):
    assert isinstance(parent_element, rng_grammar.RngGrammar), \
        'Start only expected to be in grammar'

    try:
        combine = builder.get_attribute(attrs, 'combine').strip()
    except LookupError:
        combine = ''

    return (parent_element.add_start(RngStart(combine)), {
        'attribute': rng_attribute.rng_attribute,
        'choice': rng_choice.rng_choice,
        'data': rng_data.rng_data,
        'element': rng_element.rng_element,
        'empty': rng_empty.rng_empty,
        'externalRef': builder.noop_handler,
        'group': rng_group.rng_group,
        'interleave': rng_interleave.rng_interleave,
        'list': rng_list.rng_list,
        'mixed': builder.rng_mixed,
        'notAllowed': rng_notAllowed.rng_notAllowed,
        'oneOrMore': rng_oneOrMore.rng_oneOrMore,
        'optional': builder.rng_optional,
        'parentRef': builder.noop_handler,
        'ref': rng_ref.rng_ref,
        'text': rng_text.rng_text,
        'value': rng_value.rng_value,
        'zeroOrMore': builder.rng_zeroOrMore,
    })


class RngStart(base.RngBase):
    def __init__(self, combine=''):
        super(RngStart, self).__init__()

        self.pattern = None
        self.not_allowed = False

        # Temporary for handling of multiple starts.
        self.combine = combine

    @method_once
    def finalize(self, grammar, builder):
        assert (len(self.children) == 1 and
                utils.is_pattern(self.children[0])), \
            'Wrong content of start'

        self.pattern = self.children[0].finalize(grammar, builder)

        if isinstance(self.pattern, rng_element.RngElement):
            self.pattern = self.prefinalize(grammar, builder)

        return super(RngStart, self).finalize(grammar, builder)

    def dump(self, context):
        with utils.RngTagGuard('start', context):
            self.pattern.dump(context)
