# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import rng_anyName
import rng_attribute
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
import rng_text
import rng_utils
import rng_value


def rng_element(attrs, parent_element, factory, grammar_path, all_grammars):
    elem = RngElement(attrs, factory)
    parent_element.children.append(elem)

    return (elem, {
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


class RngElement(rng_base.RngBase):
    def __init__(self, attrs, factory):
        super(RngElement, self).__init__(attrs)

        try:
            text_name = factory.get_attribute(attrs, 'name').strip()
            name = rng_name.RngName({}, text_name, factory)
            self.children.append(name)
        except LookupError:
            pass

        # Temporary for dumping to RNG.
        self.define_name = None

        self.name = None
        self.pattern = None
        self.not_allowed = False

    @method_once
    def finalize_name(self, grammar, factory):
        assert rng_utils.is_name_class(self.children[0]), \
            'Wrong name in element'
        self.name = self.children[0]
        self.name.finalize(grammar, factory)

    @method_once
    def finalize(self, grammar, factory):
        self.finalize_name(grammar, factory)

        patterns = []
        for c in self.children[1:]:
            assert rng_utils.is_pattern(c), 'Wrong content of element'

            if isinstance(c, rng_ref.RngRef):
                c = c.get_ref_pattern(grammar)

            if isinstance(c, rng_attribute.RngAttribute):
                c = c.simplify_name(grammar, factory)

            patterns.append(c)

        assert patterns, 'Wrong pattern in element'
        if len(patterns) == 1:
            self.pattern = patterns[0]
        else:
            self.pattern = rng_group.RngGroup({})
            self.pattern.children = patterns

        self.pattern = self.pattern.finalize(grammar, factory)

        return super(RngElement, self).finalize(grammar, factory)

    def define_and_simplify_name(self, grammar, factory):
        if self.define_name is None:
            assert rng_utils.is_name_class(self.name), 'Element has bad name'

            if isinstance(self.name, rng_choice.RngChoiceName):
                choice = rng_choice.RngChoicePattern({})
                for n in self.name.name_classes:
                    child = RngElement({}, factory)
                    child.children.append(n)
                    child.children.extend(self.children[1:])
                    choice.children.append(child)

                choice.finalize(grammar, factory)
                return choice

            if isinstance(self.name, rng_name.RngName):
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

            assert name not in grammar.named_elements, \
                'Invalid name for define'
            self.define_name = name
            grammar.named_elements[name] = self

        return self

    def dump_element_ref(self, fhandle, indent):
        fhandle.write(
            '{}<ref name="{}"/>\n'.format(' ' * indent, self.define_name))

    def _dump_internals(self, fhandle, indent):
        fhandle.write('>\n')
        self.name.dump(fhandle, indent)
        self.pattern.dump(fhandle, indent)
        return rng_base.RngBase._CLOSING_TAG
