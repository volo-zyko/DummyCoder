# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import rng_anyName
import rng_attribute
import rng_base
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
import rng_utils
import rng_value


def rng_choice(attrs, parent_element, factory, grammar_path, all_grammars):
    if (isinstance(parent_element, RngChoiceName) or
        isinstance(parent_element, rng_except.RngExceptName) or
        ((isinstance(parent_element, rng_element.RngElement) or
          isinstance(parent_element, rng_attribute.RngAttribute)) and
         not parent_element.children)):
        choice = RngChoiceName(attrs, parent_element)
        parent_element.children.append(choice)

        return (choice, {
            'anyName': rng_anyName.rng_anyName,
            'choice': rng_choice,
            'name': rng_name.rng_name,
            'nsName': rng_nsName.rng_nsName,
        })
    else:
        choice = RngChoicePattern(attrs, parent_element)
        parent_element.children.append(choice)

        return (choice, {
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


class RngChoicePattern(rng_base.RngBase):
    def __init__(self, attrs, parent_element):
        super(RngChoicePattern, self).__init__(attrs, parent_element)

        self.patterns = []

    @method_once
    def finalize(self, grammar, all_schemata, factory):
        has_empty = False
        for c in self.children:
            assert rng_utils.is_pattern(c), 'Wrong content of choice pattern'

            if isinstance(c, rng_ref.RngRef):
                c = c.get_element(grammar)

            if isinstance(c, rng_empty.RngEmpty):
                has_empty = True
                continue

            c.finalize(grammar, all_schemata, factory)

            if ((isinstance(c, RngChoicePattern) or
                 isinstance(c, rng_group.RngGroup) or
                 isinstance(c, rng_interleave.RngInterleave) or
                 isinstance(c, rng_oneOrMore.RngOneOrMore)) and
                len(c.patterns) == 0):
                continue

            if ((isinstance(c, RngChoicePattern) or
                 isinstance(c, rng_group.RngGroup) or
                 isinstance(c, rng_interleave.RngInterleave)) and
                len(c.patterns) == 1):
                c = c.patterns[0]

            if isinstance(c, rng_element.RngElement):
                rng_utils.set_define_name_for_element(c, grammar)

            self.patterns.append(c)

        if has_empty and self.patterns:
            self.patterns.insert(0, rng_empty.RngEmpty({}, self))

        super(RngChoicePattern, self).finalize(grammar, all_schemata, factory)

    def _tag_name(self):
        return 'choice'

    def _dump_internals(self, fhandle, indent):
        assert self.patterns, 'Empty choice pattern'

        fhandle.write('>\n')
        for p in self.patterns:
            if isinstance(p, rng_element.RngElement):
                fhandle.write(
                    '{}<ref name="{}"/>\n'.format(' ' * indent, p.define_name))
            else:
                p.dump(fhandle, indent)

        return rng_base.RngBase._CLOSING_TAG


class RngChoiceName(rng_base.RngBase):
    def __init__(self, attrs, parent_element):
        super(RngChoiceName, self).__init__(attrs, parent_element)

        self.name_classes = []

    @method_once
    def finalize(self, grammar, all_schemata, factory):
        for c in self.children:
            assert rng_utils.is_name_class(c), 'Wrong content of choice name'

            c.finalize(grammar, all_schemata, factory)

            self.name_classes.append(c)

        super(RngChoiceName, self).finalize(grammar, all_schemata, factory)

    def _tag_name(self):
        return 'choice'

    def _dump_internals(self, fhandle, indent):
        assert self.name_classes, 'Empty choice name'

        fhandle.write('>\n')
        for n in self.name_classes:
            n.dump(fhandle, indent)

        return rng_base.RngBase._CLOSING_TAG
