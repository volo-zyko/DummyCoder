# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_attribute
import rng_base
import rng_choice
import rng_data
import rng_element
import rng_empty
import rng_group
import rng_list
import rng_oneOrMore
import rng_ref
import rng_text
import rng_value


def rng_interleave(attrs, parent_element, factory, grammar_path, all_grammars):
    interleave = RngInterleave(attrs, parent_element, grammar_path)
    parent_element.children.append(interleave)

    return (interleave, {
        'attribute': rng_attribute.rng_attribute,
        'choice': rng_choice.rng_choice,
        'data': rng_data.rng_data,
        'element': rng_element.rng_element,
        'empty': rng_empty.rng_empty,
        'externalRef': factory.noop_handler,
        'group': rng_group.rng_group,
        'interleave': rng_interleave,
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


class RngInterleave(rng_base.RngBase):
    def __init__(self, attrs, parent_element, grammar_path):
        super(RngInterleave, self).__init__(attrs, parent_element)
