# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import rng_anyName
import rng_attribute
import rng_data
import rng_element
import rng_empty
import rng_except
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


def rng_choice(attrs, parent_element, factory, grammar_path, all_grammars):
    if (isinstance(parent_element, RngChoiceName) or
        isinstance(parent_element, rng_except.RngExceptName) or
        ((isinstance(parent_element, rng_element.RngElement) or
          isinstance(parent_element, rng_attribute.RngAttribute)) and
         not parent_element.children)):
        parent_element.children.append(RngChoiceName())

        return (parent_element.children[-1], {
            'anyName': rng_anyName.rng_anyName,
            'choice': rng_choice,
            'name': rng_name.rng_name,
            'nsName': rng_nsName.rng_nsName,
        })
    else:
        parent_element.children.append(RngChoicePattern())

        return (parent_element.children[-1], {
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
            'notAllowed': rng_notAllowed.rng_notAllowed,
            'oneOrMore': rng_oneOrMore.rng_oneOrMore,
            'optional': factory.rng_optional,
            'parentRef': factory.noop_handler,
            'ref': rng_ref.rng_ref,
            'text': rng_text.rng_text,
            'value': rng_value.rng_value,
            'zeroOrMore': factory.rng_zeroOrMore,
        })


class RngChoicePattern(base.RngBase):
    def __init__(self):
        super(RngChoicePattern, self).__init__()

        self.patterns = []

    @method_once
    def finalize(self, grammar, factory):
        has_empty = False
        for c in self.children:
            assert utils.is_pattern(c), 'Wrong content of choice pattern'

            if isinstance(c, rng_ref.RngRef):
                c = c.finalize(grammar, factory)

            if isinstance(c, rng_empty.RngEmpty):
                has_empty = True
                continue
            elif isinstance(c, rng_element.RngElement):
                self.patterns.append(c.prefinalize(grammar, factory))
                continue

            c = c.finalize(grammar, factory)

            if ((isinstance(c, RngChoicePattern) or
                    isinstance(c, rng_group.RngGroup) or
                    isinstance(c, rng_interleave.RngInterleave) or
                    isinstance(c, rng_oneOrMore.RngOneOrMore)) and
                    len(c.patterns) == 0):
                continue
            elif ((isinstance(c, RngChoicePattern) or
                    isinstance(c, rng_group.RngGroup) or
                    isinstance(c, rng_interleave.RngInterleave)) and
                    len(c.patterns) == 1):
                c = c.patterns[0]
            elif isinstance(c, rng_notAllowed.RngNotAllowed):
                continue

            self.patterns.append(c)

        if has_empty and self.patterns:
            self.patterns.insert(0, rng_empty.RngEmpty())

        return super(RngChoicePattern, self).finalize(grammar, factory)

    def dump(self, context):
        assert self.patterns, 'Empty choice pattern'

        with utils.RngTagGuard('choice', context):
            for (i, p) in enumerate(self.patterns):
                assert not isinstance(p, rng_empty.RngEmpty) or i == 0, \
                    'Empty is allowed only as first pattern'
                p.dump(context)


class RngChoiceName(base.RngBase):
    def __init__(self):
        super(RngChoiceName, self).__init__()

        self.name_classes = []

    @method_once
    def finalize(self, grammar, factory):
        for c in self.children:
            assert utils.is_name_class(c), 'Wrong content of choice name'

            c.finalize(grammar, factory)
            self.name_classes.append(c)

        assert len(self.name_classes) > 0, 'Wrong content of choice name'

        super(RngChoiceName, self).finalize(grammar, factory)

    def dump(self, context):
        assert self.name_classes, 'Empty choice name'

        with utils.RngTagGuard('choice', context):
            for n in self.name_classes:
                n.dump(context)
