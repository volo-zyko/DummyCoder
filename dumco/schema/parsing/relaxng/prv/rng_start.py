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


def rng_start(attrs, parent_element, factory, grammar_path, all_grammars):
    assert isinstance(parent_element, rng_grammar.RngGrammar), \
        'Start only expected to be in grammar'

    start = RngStart(attrs, factory)
    start = parent_element.add_start(start)

    return (start, {
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


class RngStart(rng_base.RngBase):
    def __init__(self, attrs, factory):
        super(RngStart, self).__init__(attrs)

        # Temporary for handling of multiple starts.
        try:
            self.combine = factory.get_attribute(attrs, 'combine').strip()
        except LookupError:
            self.combine = ''

        self.pattern = None
        self.not_allowed = False

    @method_once
    def finalize(self, grammar, factory):
        assert (len(self.children) == 1 and
                rng_utils.is_pattern(self.children[0])), \
            'Wrong content of start'

        if isinstance(self.children[0], rng_ref.RngRef):
            self.pattern = self.children[0].get_ref_pattern(grammar)
        else:
            self.pattern = self.children[0]

        self.pattern.finalize(grammar, factory)

        if isinstance(self.pattern, rng_element.RngElement):
            self.pattern = self.pattern.define_and_simplify_name(
                grammar, factory)

        return super(RngStart, self).finalize(grammar, factory)

    def _dump_internals(self, fhandle, indent):
        fhandle.write('>\n')
        if isinstance(self.pattern, rng_element.RngElement):
            self.pattern.dump_element_ref(fhandle, indent)
        else:
            self.pattern.dump(fhandle, indent)

        return rng_base.RngBase._CLOSING_TAG
