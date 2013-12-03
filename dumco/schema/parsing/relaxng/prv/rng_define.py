# Distributed under the GPLv2 License; see accompanying file COPYING.

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
import rng_oneOrMore
import rng_ref
import rng_text
import rng_value


def rng_define(attrs, parent_element, factory, grammar_path, all_grammars):
    assert isinstance(parent_element, rng_grammar.RngGrammar), \
        'Define only expected to be in grammar'

    define = RngDefine(attrs, parent_element, grammar_path, factory)
    define = parent_element.add_define(define, grammar_path)

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
        'notAllowed': factory.noop_handler,
        'oneOrMore': rng_oneOrMore.rng_oneOrMore,
        'optional': factory.rng_optional,
        'parentRef': factory.noop_handler,
        'ref': rng_ref.rng_ref,
        'text': rng_text.rng_text,
        'value': rng_value.rng_value,
        'zeroOrMore': factory.rng_zeroOrMore,
    })


class RngDefine(rng_base.RngBase):
    def __init__(self, attrs, parent_element, grammar_path, factory):
        super(RngDefine, self).__init__(attrs, parent_element)

        self.finalized = False

        self.name = factory.get_attribute(attrs, 'name').strip()
        try:
            self.combine = factory.get_attribute(attrs, 'combine').strip()
        except LookupError:
            self.combine = ''

    def finalize(self, grammar, all_schemata, factory):
        if not self.finalized:
            self.finalized = True
            super(RngDefine, self).finalize(grammar, all_schemata, factory)

    def _dump_internals(self, fhandle, indent): # pragma: no cover
        fhandle.write(' name="{}"'.format(self.name))
        return super(RngDefine, self)._dump_internals(fhandle, indent)
