# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import rng_attribute
import rng_choice
import rng_data
import rng_element
import rng_empty
import rng_group
import rng_interleave
import rng_list
import rng_notAllowed
import rng_ref
import rng_text
import rng_value
import utils


def rng_oneOrMore(attrs, parent_element, factory, grammar_path, all_grammars):
    parent_element.children.append(RngOneOrMore())

    return (parent_element.children[-1], {
        'attribute': rng_attribute.rng_attribute,
        'choice': rng_choice.rng_choice,
        'data': rng_data.rng_data,
        'element': rng_element.rng_element,
        'empty': rng_empty.rng_empty,
        'externalRef': factory.noop_handler,
        'group': rng_group.rng_group,
        'interleave': rng_interleave.rng_interleave,
        'list': rng_list.rng_list,
        'mixed': factory.rng_mixed,
        'notAllowed': rng_notAllowed.rng_notAllowed,
        'oneOrMore': rng_oneOrMore,
        'optional': factory.rng_optional,
        'parentRef': factory.noop_handler,
        'ref': rng_ref.rng_ref,
        'text': rng_text.rng_text,
        'value': rng_value.rng_value,
        'zeroOrMore': factory.rng_zeroOrMore,
    })


class RngOneOrMore(base.RngBase):
    def __init__(self):
        super(RngOneOrMore, self).__init__()

        self.patterns = []

    @method_once
    def finalize(self, grammar, factory):
        for c in self.children:
            assert utils.is_pattern(c), 'Wrong content of oneOrMore'

            if isinstance(c, rng_ref.RngRef):
                c = c.finalize(grammar, factory)

            if isinstance(c, rng_empty.RngEmpty):
                continue
            elif isinstance(c, rng_element.RngElement):
                self.patterns.append(c.prefinalize(grammar, factory))
                continue

            c = c.finalize(grammar, factory)

            if ((isinstance(c, rng_choice.RngChoicePattern) or
                    isinstance(c, rng_group.RngGroup) or
                    isinstance(c, rng_interleave.RngInterleave) or
                    isinstance(c, RngOneOrMore)) and
                    len(c.patterns) == 0):
                continue
            elif ((isinstance(c, rng_choice.RngChoicePattern) or
                    isinstance(c, rng_group.RngGroup) or
                    isinstance(c, rng_interleave.RngInterleave)) and
                    len(c.patterns) == 1):
                c = c.patterns[0]
            elif isinstance(c, rng_notAllowed.RngNotAllowed):
                return c

            self.patterns.append(c)

        if len(self.patterns) > 1:
            group = rng_group.RngGroup()
            group.finalize(grammar, factory)
            group.patterns = self.patterns
            self.patterns = [group]

        return super(RngOneOrMore, self).finalize(grammar, factory)

    def dump(self, context):
        assert self.patterns, 'Empty oneOrMore pattern'

        with utils.RngTagGuard('oneOrMore', context):
            for p in self.patterns:
                assert not isinstance(p, rng_empty.RngEmpty), \
                    'Empty is not allowed'
                p.dump(context)
