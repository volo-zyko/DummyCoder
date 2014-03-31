# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import rng_attribute
import rng_base
import rng_choice
import rng_data
import rng_element
import rng_empty
import rng_interleave
import rng_list
import rng_notAllowed
import rng_oneOrMore
import rng_ref
import rng_text
import rng_utils
import rng_value


def rng_group(attrs, parent_element, factory, grammar_path, all_grammars):
    group = RngGroup(attrs)
    parent_element.children.append(group)

    return (group, {
        'attribute': rng_attribute.rng_attribute,
        'choice': rng_choice.rng_choice,
        'data': rng_data.rng_data,
        'element': rng_element.rng_element,
        'empty': rng_empty.rng_empty,
        'externalRef': factory.noop_handler,
        'group': rng_group,
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


class RngGroup(rng_base.RngBase):
    def __init__(self, attrs):
        super(RngGroup, self).__init__(attrs)

        self.patterns = []

    @method_once
    def finalize(self, grammar, factory):
        for c in self.children:
            assert rng_utils.is_pattern(c), 'Wrong content of group'

            if isinstance(c, rng_ref.RngRef):
                c = c.get_ref_pattern(grammar)

            if isinstance(c, rng_empty.RngEmpty):
                continue
            elif isinstance(c, rng_element.RngElement):
                c.finalize_name(grammar, factory)
                c = c.define_and_simplify_name(grammar, factory)
                self.patterns.append(c)
                continue
            elif isinstance(c, rng_attribute.RngAttribute):
                c = c.simplify_name(grammar, factory)

            c = c.finalize(grammar, factory)

            if ((isinstance(c, rng_choice.RngChoicePattern) or
                    isinstance(c, RngGroup) or
                    isinstance(c, rng_interleave.RngInterleave) or
                    isinstance(c, rng_oneOrMore.RngOneOrMore)) and
                    len(c.patterns) == 0):
                continue
            elif ((isinstance(c, rng_choice.RngChoicePattern) or
                    isinstance(c, RngGroup) or
                    isinstance(c, rng_interleave.RngInterleave)) and
                    len(c.patterns) == 1):
                c = c.patterns[0]
            elif isinstance(c, rng_notAllowed.RngNotAllowed):
                return c

            self.patterns.append(c)

        return super(RngGroup, self).finalize(grammar, factory)

    def _dump_internals(self, fhandle, indent):
        assert self.patterns, 'Empty group pattern'

        fhandle.write('>\n')
        for p in self.patterns:
            if isinstance(p, rng_element.RngElement):
                p.dump_element_ref(fhandle, indent)
            else:
                p.dump(fhandle, indent)

        return rng_base.RngBase._CLOSING_TAG
