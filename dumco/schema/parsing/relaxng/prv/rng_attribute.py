# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import rng_anyName
import rng_base
import rng_choice
import rng_data
import rng_element
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
import rng_utils
import rng_value


def rng_attribute(attrs, parent_element, factory, grammar_path, all_grammars):
    attr = RngAttribute(attrs, parent_element, factory)
    parent_element.children.append(attr)

    return (attr, {
        'anyName': rng_anyName.rng_anyName,
        'choice': rng_choice.rng_choice,
        'data': rng_data.rng_data,
        'element': rng_element.rng_element,
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


class RngAttribute(rng_base.RngBase):
    def __init__(self, attrs, parent_element, factory):
        super(RngAttribute, self).__init__(attrs, parent_element)

        try:
            ns = factory.get_attribute(attrs, 'ns')
        except LookupError:
            ns = ''

        factory.ns_attribute_stack.append(ns)
        try:
            name = rng_name.RngName(
                {}, parent_element,
                factory.get_attribute(attrs, 'name').strip(), factory)

            self.children.append(name)
        except LookupError:
            pass
        factory.ns_attribute_stack.pop()

        self.name = None
        self.pattern = None

    @method_once
    def finalize(self, grammar, factory):
        assert rng_utils.is_name_class(self.children[0]), \
            'Wrong name in attribute'
        self.name = self.children[0]
        self.name.finalize(grammar, factory)

        for c in self.children[1:]:
            assert rng_utils.is_pattern(c), 'Wrong content of attribute'

            c.finalize(grammar, factory)

            assert self.pattern is None, 'Wrong pattern in attribute'
            if isinstance(c, rng_ref.RngRef):
                self.pattern = c.get_ref_pattern(grammar)
            else:
                self.pattern = c

        if self.pattern is None:
            self.pattern = rng_text.RngText({}, self)

        super(RngAttribute, self).finalize(grammar, factory)

    def _dump_internals(self, fhandle, indent):
        fhandle.write('>\n')
        self.name.dump(fhandle, indent)
        self.pattern.dump(fhandle, indent)
        return rng_base.RngBase._CLOSING_TAG
