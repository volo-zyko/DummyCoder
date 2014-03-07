# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import rng_attribute
import rng_base
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
import rng_utils
import rng_value


def rng_define(attrs, parent_element, factory, grammar_path, all_grammars):
    assert isinstance(parent_element, rng_grammar.RngGrammar), \
        'Define only expected to be in grammar'

    define = RngDefine(attrs, parent_element, factory)
    define = parent_element.add_define(define)

    return (define, {
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
        'oneOrMore': rng_oneOrMore.rng_oneOrMore,
        'optional': factory.rng_optional,
        'parentRef': factory.noop_handler,
        'ref': rng_ref.rng_ref,
        'text': rng_text.rng_text,
        'value': rng_value.rng_value,
        'zeroOrMore': factory.rng_zeroOrMore,
    })


class RngDefine(rng_base.RngBase):
    def __init__(self, attrs, parent_element, factory):
        super(RngDefine, self).__init__(attrs, parent_element)

        # Temporary for handling of multiple defines with same name.
        try:
            self.combine = factory.get_attribute(attrs, 'combine').strip()
        except LookupError:
            self.combine = ''

        self.pattern = None
        self.name = factory.get_attribute(attrs, 'name').strip()

    @method_once
    def prefinalize(self, grammar):
        if self.pattern is not None:
            return

        if len(self.children) == 1:
            assert rng_utils.is_pattern(self.children[0]), \
                'Wrong content of define'
            self.pattern = self.children[0]
            if isinstance(self.pattern, rng_ref.RngRef):
                self.pattern = self.pattern.get_ref_pattern(grammar)
        else:
            patterns = []
            for c in self.children:
                assert rng_utils.is_pattern(c), 'Wrong content of define'

                patterns.append(c)

            assert patterns, 'Wrong pattern in define'
            self.pattern = rng_group.RngGroup({}, self)
            self.pattern.children = patterns
