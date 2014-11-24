# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import xsd_simple_type


def xsd_list(attrs, parent_element, factory, schema_path, all_schemata):
    new_element = XsdList(attrs, all_schemata[schema_path])
    parent_element.children.append(new_element)

    return (new_element, {
        'annotation': factory.noop_handler,
        'simpleType': xsd_simple_type.xsd_simpleType,
    })


class XsdList(base.XsdBase):
    def __init__(self, attrs, parent_schema):
        super(XsdList, self).__init__(attrs)

        self.schema = parent_schema
        self.itemtype = None

    @method_once
    def finalize(self, factory):
        if self.attr('itemType') is None:
            for t in self.children:
                assert (isinstance(t, xsd_simple_type.XsdSimpleType) and
                        self.itemtype is None), \
                    'Wrong content of List'

                self.itemtype = t.finalize(factory)
        else:
            self.itemtype = \
                factory.resolve_simple_type(self.attr('itemType'), self.schema)

        return self
