# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_anyName
import rng_attribute
import rng_base
import rng_data
import rng_element
import rng_empty
import rng_group
import rng_interleave
import rng_list
import rng_name
import rng_nsName
import rng_oneOrMore
import rng_ref
import rng_text
import rng_value


def rng_choice(attrs, parent_element, factory, grammar_path, all_grammars):
    choice = RngChoice(attrs, parent_element, grammar_path)
    parent_element.children.append(choice)

    return (choice, {
        'anyName': rng_anyName.rng_anyName,
        'attribute': rng_attribute.rng_attribute,
        'choice': rng_choice,
        'data': rng_data.rng_data,
        'element': rng_element.rng_element,
        'empty': rng_empty.rng_empty,
        'externalRef': factory.noop_handler,
        'group': rng_group.rng_group,
        'interleave': rng_interleave.rng_interleave,
        'list': rng_list.rng_list,
        'mixed': factory.rng_mixed,
        'name': rng_name.rng_name,
        'notAllowed': factory.noop_handler,
        'nsName': rng_nsName.rng_nsName,
        'oneOrMore': rng_oneOrMore.rng_oneOrMore,
        'optional': factory.rng_optional,
        'parentRef': factory.noop_handler,
        'ref': rng_ref.rng_ref,
        'text': rng_text.rng_text,
        'value': rng_value.rng_value,
        'zeroOrMore': factory.rng_zeroOrMore,
    })


class RngChoice(rng_base.RngBase):
    def __init__(self, attrs, parent_element, grammar_path):
        super(RngChoice, self).__init__(attrs, parent_element)
