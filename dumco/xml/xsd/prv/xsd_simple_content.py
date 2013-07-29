# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import xsd_base
import xsd_extension_sc
import xsd_restriction_sc


def xsd_simpleContent(attrs, parent_element, factory,
                      schema_path, all_schemata):
    new_element = XsdSimpleContent(attrs)
    parent_element.children.append(new_element)

    return (new_element, {
        'annotation': factory.noop_handler,
        'extension': xsd_extension_sc.xsd_extension_in_simpleContent,
        'restriction': xsd_restriction_sc.xsd_restriction_in_simpleContent,
    })


class XsdSimpleContent(xsd_base.XsdBase):
    def __init__(self, attrs):
        super(XsdSimpleContent, self).__init__(attrs)

        self.base = None
        self.attributes = []

    @method_once
    def finalize(self, factory):
        for c in self.children:
            assert ((isinstance(c, xsd_extension_sc.XsdSimpleExtension) or
                     isinstance(c, xsd_restriction_sc.XsdSimpleRestriction)) and
                    self.base is None), 'Wrong content of SimpleContent'

            c.finalize(factory)

            self.base = c.base
            self.attributes = c.attributes

        return self
