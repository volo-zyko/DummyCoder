# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.schema.rng_types import RNG_NAMESPACE
from dumco.utils.decorators import method_once

import base
import rng_anyName
import rng_attribute
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


def rng_element(attrs, parent_element, factory, grammar_path, all_grammars):
    try:
        text_name = factory.get_attribute(attrs, 'name').strip()
        name_obj = rng_name.create_name(text_name, factory)
    except LookupError:
        name_obj = None

    parent_element.children.append(RngElement(name_obj))

    return (parent_element.children[-1], {
        'anyName': rng_anyName.rng_anyName,
        'attribute': rng_attribute.rng_attribute,
        'choice': rng_choice.rng_choice,
        'data': rng_data.rng_data,
        'element': rng_element,
        'empty': rng_empty.rng_empty,
        'externalRef': factory.noop_handler,
        'group': rng_group.rng_group,
        'interleave': rng_interleave.rng_interleave,
        'list': rng_list.rng_list,
        'mixed': factory.rng_mixed,
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


class RngElement(base.RngBase):
    def __init__(self, name):
        super(RngElement, self).__init__()

        self.name = name
        self.pattern = None
        self.not_allowed = False

        # Temporary for dumping to RNG.
        self.define_name = None

    @method_once
    def prefinalize(self, grammar, factory):
        if self.name is None:
            assert utils.is_name_class(self.children[0]), \
                'Wrong name in element'

            self.name = self.children[0]
            self.name.finalize(grammar, factory)

            self.children = self.children[1:]

        if isinstance(self.name, rng_choice.RngChoiceName):
            choice = rng_choice.RngChoicePattern()
            for n in self.name.name_classes:
                child = RngElement(n)
                child.children.append(n)
                child.children.extend(self.children)
                choice.children.append(child)
            return choice
        elif isinstance(self.name, rng_name.RngName):
            if self.name.ns in grammar.known_prefixes:
                prefix = grammar.known_prefixes[self.name.ns]
                name = '{}-{}-element'.format(prefix, self.name.name)
            else:
                name = '{}-element'.format(self.name.name)
        elif (isinstance(self.name, rng_anyName.RngAnyName) or
              isinstance(self.name, rng_nsName.RngNsName)):
            name = 'any'

        if name in grammar.named_elements:
            name = '{}{}'.format(name, grammar.element_counter)
            grammar.element_counter += 1

        assert name not in grammar.named_elements, 'Invalid name for define'

        self.define_name = name
        grammar.named_elements[name] = self

        return self

    @method_once
    def finalize(self, grammar, factory):
        self.prefinalize(grammar, factory)

        patterns = []
        has_empty = False
        for c in self.children:
            assert utils.is_pattern(c), 'Wrong content of element'

            if isinstance(c, rng_ref.RngRef):
                c = c.finalize(grammar, factory)

            if isinstance(c, rng_empty.RngEmpty):
                has_empty = True
                continue
            elif isinstance(c, RngElement):
                patterns.append(c.prefinalize(grammar, factory))
                continue

            c = c.finalize(grammar, factory)

            if ((isinstance(c, rng_choice.RngChoicePattern) or
                    isinstance(c, rng_group.RngGroup) or
                    isinstance(c, rng_interleave.RngInterleave) or
                    isinstance(c, rng_oneOrMore.RngOneOrMore)) and
                    len(c.patterns) == 0):
                has_empty = True
                continue
            elif ((isinstance(c, rng_choice.RngChoicePattern) or
                    isinstance(c, rng_group.RngGroup) or
                    isinstance(c, rng_interleave.RngInterleave)) and
                    len(c.patterns) == 1):
                c = c.patterns[0]

            patterns.append(c)

        assert has_empty or patterns, 'Wrong pattern in element'

        if not patterns:
            self.pattern = rng_empty.RngEmpty()
        elif len(patterns) == 1:
            self.pattern = patterns[0]
        else:
            self.pattern = rng_group.RngGroup()
            self.pattern.children = patterns

        self.pattern = self.pattern.finalize(grammar, factory)

        return super(RngElement, self).finalize(grammar, factory)

    def dump(self, context):
        if context.parent_stack[-2] == RNG_NAMESPACE + ':define':
            with utils.RngTagGuard('ref', context):
                context.add_attribute('name', self.define_name)
        else:
            with utils.RngTagGuard('element', context):
                self.name.dump(context)
                self.pattern.dump(context)
