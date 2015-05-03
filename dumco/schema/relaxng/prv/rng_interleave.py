# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import rng_attribute
import rng_choice
import rng_data
import rng_element
import rng_empty
import rng_group
import rng_list
import rng_notAllowed
import rng_oneOrMore
import rng_ref
import rng_text
import rng_value
import utils


def rng_interleave(attrs, parent_element, builder, grammar_path, all_grammars):
    parent_element.children.append(RngInterleave())

    return (parent_element.children[-1], {
        'attribute': rng_attribute.rng_attribute,
        'choice': rng_choice.rng_choice,
        'data': rng_data.rng_data,
        'element': rng_element.rng_element,
        'empty': rng_empty.rng_empty,
        'externalRef': builder.noop_handler,
        'group': rng_group.rng_group,
        'interleave': rng_interleave,
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


class RngInterleave(base.RngBase):
    def __init__(self, ):
        super(RngInterleave, self).__init__()

        self.patterns = []

    @method_once
    def finalize(self, grammar, builder):
        for c in self.children:
            assert utils.is_pattern(c), 'Wrong content of interleave'

            if isinstance(c, rng_ref.RngRef):
                c = c.finalize(grammar, builder)

            if isinstance(c, rng_empty.RngEmpty):
                continue
            elif isinstance(c, rng_element.RngElement):
                self.patterns.append(c.prefinalize(grammar, builder))
                continue

            c = c.finalize(grammar, builder)

            if ((isinstance(c, rng_choice.RngChoicePattern) or
                    isinstance(c, rng_group.RngGroup) or
                    isinstance(c, RngInterleave) or
                    isinstance(c, rng_oneOrMore.RngOneOrMore)) and
                    len(c.patterns) == 0):
                continue
            elif ((isinstance(c, rng_choice.RngChoicePattern) or
                    isinstance(c, rng_group.RngGroup) or
                    isinstance(c, RngInterleave)) and
                    len(c.patterns) == 1):
                c = c.patterns[0]
            elif isinstance(c, rng_notAllowed.RngNotAllowed):
                return c

            self.patterns.append(c)

        return super(RngInterleave, self).finalize(grammar, builder)

    def dump(self, context):
        assert self.patterns, 'Empty interleave pattern'

        with utils.RngTagGuard('interleave', context):
            for p in self.patterns:
                assert not isinstance(p, rng_empty.RngEmpty), \
                    'Empty is not allowed'
                p.dump(context)
