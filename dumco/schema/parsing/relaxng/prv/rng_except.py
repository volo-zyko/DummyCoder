# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import rng_anyName
import rng_base
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
import rng_utils
import rng_value


def rng_except(attrs, parent_element, factory, grammar_path, all_grammars):
    if isinstance(parent_element, rng_data.RngData):
        excpt = RngExceptPattern(attrs, parent_element)
        parent_element.children.append(excpt)

        return (excpt, {
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
        excpt = RngExceptName(attrs, parent_element)
        parent_element.children.append(excpt)

        return (excpt, {
            'anyName': rng_anyName.rng_anyName,
            'choice': rng_choice.rng_choice,
            'name': rng_name.rng_name,
            'nsName': rng_nsName.rng_nsName,
        })


class RngExceptPattern(rng_base.RngBase):
    def __init__(self, attrs, parent_element):
        super(RngExceptPattern, self).__init__(attrs, parent_element)

        self.patterns = []

    @method_once
    def finalize(self, grammar, factory):
        for c in self.children:
            assert rng_utils.is_pattern(c), 'Wrong content of execept pattern'

            if isinstance(c, rng_ref.RngRef):
                c = c.get_ref_pattern(grammar)

            c.finalize(grammar, factory)

            if ((isinstance(c, rng_choice.RngChoicePattern) or
                    isinstance(c, rng_group.RngGroup) or
                    isinstance(c, rng_interleave.RngInterleave) or
                    isinstance(c, rng_oneOrMore.RngOneOrMore)) and
                    len(c.patterns) == 0):
                continue

            if ((isinstance(c, rng_choice.RngChoicePattern) or
                    isinstance(c, rng_group.RngGroup) or
                    isinstance(c, rng_interleave.RngInterleave)) and
                    len(c.patterns) == 1):
                c = c.patterns[0]

            self.patterns.append(c)

        super(RngExceptPattern, self).finalize(grammar, factory)

    def _tag_name(self):
        return 'except'

    def _dump_internals(self, fhandle, indent):
        assert self.patterns, 'Empty except pattern'

        fhandle.write('>\n')
        for p in self.patterns:
            p.dump(fhandle, indent)

        return rng_base.RngBase._CLOSING_TAG


class RngExceptName(rng_base.RngBase):
    def __init__(self, attrs, parent_element):
        super(RngExceptName, self).__init__(attrs, parent_element)

        self.name_classes = []

    @method_once
    def finalize(self, grammar, factory):
        for c in self.children:
            assert rng_utils.is_name_class(c), 'Wrong content of except name'

            c.finalize(grammar, factory)
            self.name_classes.append(c)

        if len(self.name_classes) > 1:
            choice = rng_choice.RngChoiceName({}, self)
            choice.name_classes = self.name_classes
            self.name_classes = [choice]

        super(RngExceptName, self).finalize(grammar, factory)

    def _tag_name(self):
        return 'except'

    def _dump_internals(self, fhandle, indent):
        assert self.name_classes, 'Empty except name'

        fhandle.write('>\n')
        for n in self.name_classes:
            n.dump(fhandle, indent)

        return rng_base.RngBase._CLOSING_TAG
