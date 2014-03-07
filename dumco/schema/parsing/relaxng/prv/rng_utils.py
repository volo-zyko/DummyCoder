# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_anyName
import rng_attribute
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
import rng_value


def is_name_class(value):
    if isinstance(value, rng_choice.RngChoiceName):
        return all(map(lambda p: is_name_class(p), value.name_classes))

    return (isinstance(value, rng_name.RngName) or
            isinstance(value, rng_anyName.RngAnyName) or
            isinstance(value, rng_nsName.RngNsName))


def is_pattern(value):
    return (isinstance(value, rng_attribute.RngAttribute) or
            isinstance(value, rng_choice.RngChoicePattern) or
            isinstance(value, rng_data.RngData) or
            isinstance(value, rng_element.RngElement) or
            isinstance(value, rng_empty.RngEmpty) or
            isinstance(value, rng_group.RngGroup) or
            isinstance(value, rng_interleave.RngInterleave) or
            isinstance(value, rng_list.RngList) or
            isinstance(value, rng_notAllowed.RngNotAllowed) or
            isinstance(value, rng_oneOrMore.RngOneOrMore) or
            isinstance(value, rng_ref.RngRef) or
            isinstance(value, rng_text.RngText) or
            isinstance(value, rng_value.RngValue))


def set_define_name_for_element(element, grammar):
    if element.define_name is None:
        assert is_name_class(element.name), 'Element has bad name'

        if isinstance(element.name, rng_name.RngName):
            if element.name.ns in grammar.known_prefixes:
                prefix = grammar.known_prefixes[element.name.ns]
                name = '{}-{}-element'.format(prefix, element.name.name)
            else:
                name = '{}-element'.format(element.name.name)
        elif (isinstance(element.name, rng_anyName.RngAnyName) or
              isinstance(element.name, rng_nsName.RngNsName)):
            name = 'any'
        elif isinstance(element.name, rng_choice.RngChoiceName):
            name = 'choice'

        if [e for e in grammar.elements if e.define_name == name]:
            name = '{}{}'.format(name, grammar.element_counter)
            grammar.element_counter += 1

        element.define_name = name
        grammar.elements.append(element)


def dump_element_ref(element, fhandle, indent):
    space = ' ' * indent
    fhandle.write('{}<ref name="{}"/>\n'.format(space, element.define_name))
