# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import rng_anyName
import rng_choice
import rng_data
import rng_empty
import rng_group
import rng_interleave
import rng_list
import rng_name
import rng_notAllowed
import rng_nsName
import rng_oneOrMore
import rng_ref
import rng_text
import rng_value
import utils


def rng_attribute(attrs, parent_element, factory, grammar_path, all_grammars):
    try:
        text_name = factory.get_attribute(attrs, 'name').strip()
        name_obj = rng_name.create_name(text_name, factory)
    except LookupError:
        name_obj = None

    parent_element.children.append(RngAttribute(name_obj))

    return (parent_element.children[-1], {
        'anyName': rng_anyName.rng_anyName,
        'choice': rng_choice.rng_choice,
        'data': rng_data.rng_data,
        'empty': rng_empty.rng_empty,
        'externalRef': factory.noop_handler,
        'group': rng_group.rng_group,
        'interleave': rng_interleave.rng_interleave,
        'list': rng_list.rng_list,
        'name': rng_name.rng_name,
        'notAllowed': rng_notAllowed.rng_notAllowed,
        'nsName': rng_nsName.rng_nsName,
        'oneOrMore': rng_oneOrMore.rng_oneOrMore,
        'optional': factory.rng_optional,
        'parentRef': factory.noop_handler,
        'ref': rng_ref.rng_ref,
        'text': rng_text.rng_text,
        'value': rng_value.rng_value,
        'zeroOrMore': factory.rng_zeroOrMore,
    })


class RngAttribute(base.RngBase):
    def __init__(self, name):
        super(RngAttribute, self).__init__()

        self.name = name
        self.pattern = None

        if name is not None:
            self.children.append(name)

    @method_once
    def finalize(self, grammar, factory):
        assert utils.is_name_class(self.children[0]), \
            'Wrong name in attribute'

        self.name = self.children[0]
        self.name.finalize(grammar, factory)

        if isinstance(self.name, rng_choice.RngChoiceName):
            choice = rng_choice.RngChoicePattern()

            for n in self.name.name_classes:
                child = RngAttribute(n)
                child.children.extend(self.children[1:])
                choice.children.append(child)

            return choice.finalize(grammar, factory)

        for c in self.children[1:]:
            assert utils.is_pattern(c), 'Wrong content of attribute'

            self.pattern = c.finalize(grammar, factory)

            assert self.pattern is None, 'Wrong pattern in attribute'

            if isinstance(c, rng_notAllowed.RngNotAllowed):
                return c

        if self.pattern is None:
            self.pattern = rng_text.RngText()

        return super(RngAttribute, self).finalize(grammar, factory)

    def dump(self, context):
        with utils.RngTagGuard('attribute', context):
            self.name.dump(context)
            self.pattern.dump(context)
