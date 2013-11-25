# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_attribute
import rng_base
import rng_choice
import rng_data
import rng_element
import rng_group
import rng_interleave
import rng_list
import rng_mixed
import rng_oneOrMore
import rng_optional
import rng_ref
import rng_value


def rng_zeroOrMore(attrs, parent_element, factory, schema_path, all_schemata):
    zero = RngZeroOrMore(attrs, schema_path)

    return (zero, {
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
        'notAllowed': factory.noop_handler,
        'oneOrMore': rng_oneOrMore.rng_oneOrMore,
        'optional': rng_optional.rng_optional,
        'parentRef': factory.noop_handler,
        'ref': rng_ref.rng_ref,
        'text': factory.noop_handler,
        'value': rng_value.rng_value,
        'zeroOrMore': rng_zeroOrMore,
    })


class RngZeroOrMore(rng_base.RngBase):
    def __init__(self, attrs, schema_path):
        super(RngZeroOrMore, self).__init__(attrs)
