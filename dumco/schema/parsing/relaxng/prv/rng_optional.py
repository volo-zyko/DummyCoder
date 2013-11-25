# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_attribute
import rng_base
import rng_choice
import rng_element
import rng_data
import rng_group
import rng_interleave
import rng_list
import rng_mixed
import rng_oneOrMore
import rng_ref
import rng_value
import rng_zeroOrMore


def rng_optional(attrs, parent_element, factory, schema_path, all_schemata):
    optional = RngOptional(attrs, schema_path)

    return (optional, {
        'attribute': rng_attribute.rng_attribute,
        'choice': rng_choice.rng_choice,
        'data': rng_data.rng_data,
        'element': rng_element.rng_element,
        'empty': factory.noop_handler,
        'externalRef': factory.noop_handler,
        'group': rng_group.rng_group,
        'interleave': rng_interleave.rng_interleave,
        'list': rng_list.rng_list,
        'mixed': rng_mixed.rng_mixed,
        'name': factory.noop_handler,
        'notAllowed': factory.noop_handler,
        'oneOrMore': rng_oneOrMore.rng_oneOrMore,
        'optional': rng_optional,
        'parentRef': factory.noop_handler,
        'ref': rng_ref.rng_ref,
        'text': factory.noop_handler,
        'value': rng_value.rng_value,
        'zeroOrMore': rng_zeroOrMore.rng_zeroOrMore,
    })


class RngOptional(rng_base.RngBase):
    def __init__(self, attrs, schema_path):
        super(RngOptional, self).__init__(attrs)
