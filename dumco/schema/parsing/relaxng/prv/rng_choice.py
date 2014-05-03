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
        choice = RngChoiceName(attrs)
        parent_element.children.append(choice)

        return (choice, {
            'anyName': rng_anyName.rng_anyName,
            'choice': rng_choice,
            'name': rng_name.rng_name,
            'nsName': rng_nsName.rng_nsName,
        })
    else:
        choice = RngChoicePattern(attrs)
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
    def __init__(self, attrs):
        super(RngChoicePattern, self).__init__(attrs)

        self.patterns = []

    @method_once
    def finalize(self, grammar, factory):
        has_empty = False
        for c in self.children:
            assert rng_utils.is_pattern(c), 'Wrong content of choice pattern'

            if isinstance(c, rng_ref.RngRef):
                c = c.get_ref_pattern(grammar)

            if isinstance(c, rng_empty.RngEmpty):
                has_empty = True
                continue
            elif isinstance(c, rng_element.RngElement):
                c.finalize_name(grammar, factory)
                c = c.define_and_simplify_name(grammar, factory)
                self.patterns.append(c)
                continue
            elif isinstance(c, rng_attribute.RngAttribute):
                c = c.simplify_name(grammar, factory)

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
            self.patterns.insert(0, rng_empty.RngEmpty({}))

        return super(RngChoicePattern, self).finalize(grammar, factory)

    def _tag_name(self):
        return 'choice'

    def _dump_internals(self, fhandle, indent):
        assert self.patterns, 'Empty choice pattern'

        fhandle.write('>\n')
        for (i, p) in enumerate(self.patterns):
            if isinstance(p, rng_element.RngElement):
                p.dump_element_ref(fhandle, indent)
            else:
                assert not isinstance(p, rng_empty.RngEmpty) or i == 0, \
                    'Empty is allowed only as first pattern'
                p.dump(fhandle, indent)

        return rng_base.RngBase._CLOSING_TAG


class RngChoiceName(rng_base.RngBase):
    def __init__(self, attrs):
        super(RngChoiceName, self).__init__(attrs)

        self.name_classes = []

    @method_once
    def finalize(self, grammar, factory):
        for c in self.children:
            assert rng_utils.is_name_class(c), 'Wrong content of choice name'

            c.finalize(grammar, factory)
            self.name_classes.append(c)

        assert len(self.name_classes) > 0, 'Wrong content of choice name'

        super(RngChoiceName, self).finalize(grammar, factory)

    def _tag_name(self):
        return 'choice'

    def _dump_internals(self, fhandle, indent):
        assert self.name_classes, 'Empty choice name'

        fhandle.write('>\n')
        for n in self.name_classes:
            n.dump(fhandle, indent)

        return rng_base.RngBase._CLOSING_TAG
