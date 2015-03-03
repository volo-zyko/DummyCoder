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
import rng_value
import utils


def rng_except(attrs, parent_element, factory, grammar_path, all_grammars):
    if isinstance(parent_element, rng_data.RngData):
        parent_element.children.append(RngExceptPattern())

        return (parent_element.children[-1], {
            'choice': rng_choice.rng_choice,
            'data': rng_data.rng_data,
            'empty': rng_empty.rng_empty,
            'externalRef': factory.noop_handler,
            'group': rng_group.rng_group,
            'interleave': rng_interleave.rng_interleave,
            'list': rng_list.rng_list,
            'notAllowed': rng_notAllowed.rng_notAllowed,
            'oneOrMore': rng_oneOrMore.rng_oneOrMore,
            'optional': factory.rng_optional,
            'parentRef': factory.noop_handler,
            'ref': rng_ref.rng_ref,
            'value': rng_value.rng_value,
            'zeroOrMore': factory.rng_zeroOrMore,
        })
    else:
        parent_element.children.append(RngExceptName())

        return (parent_element.children[-1], {
            'anyName': rng_anyName.rng_anyName,
            'choice': rng_choice.rng_choice,
            'name': rng_name.rng_name,
            'nsName': rng_nsName.rng_nsName,
        })


class RngExceptPattern(base.RngBase):
    def __init__(self):
        super(RngExceptPattern, self).__init__()

        self.patterns = []

    @method_once
    def finalize(self, grammar, factory):
        for c in self.children:
            assert utils.is_pattern(c), 'Wrong content of except pattern'

            c = c.finalize(grammar, factory)

            if ((isinstance(c, rng_choice.RngChoicePattern) or
                    isinstance(c, rng_group.RngGroup) or
                    isinstance(c, rng_interleave.RngInterleave) or
                    isinstance(c, rng_oneOrMore.RngOneOrMore)) and
                    len(c.patterns) == 0):
                continue
            elif ((isinstance(c, rng_choice.RngChoicePattern) or
                    isinstance(c, rng_group.RngGroup) or
                    isinstance(c, rng_interleave.RngInterleave)) and
                    len(c.patterns) == 1):
                c = c.patterns[0]
            elif isinstance(c, rng_notAllowed.RngNotAllowed):
                self.patterns = []
                return self

            self.patterns.append(c)

        return super(RngExceptPattern, self).finalize(grammar, factory)

    def dump(self, context):
        assert self.patterns, 'Empty except pattern'

        with utils.RngTagGuard('except', context):
            for p in self.patterns:
                p.dump(context)


class RngExceptName(base.RngBase):
    def __init__(self):
        super(RngExceptName, self).__init__()

        self.name_classes = []

    @method_once
    def finalize(self, grammar, factory):
        for c in self.children:
            assert utils.is_name_class(c), 'Wrong content of except name'

            c.finalize(grammar, factory)
            self.name_classes.append(c)

        assert len(self.name_classes) > 0, 'Wrong content of except name'

        if len(self.name_classes) > 1:
            choice = rng_choice.RngChoiceName({})
            choice.name_classes = self.name_classes
            self.name_classes = [choice]

        super(RngExceptName, self).finalize(grammar, factory)

    def dump(self, context):
        assert self.name_classes, 'Empty except name'

        with utils.RngTagGuard('except', context):
            for n in self.name_classes:
                n.dump(context)
