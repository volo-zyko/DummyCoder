# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import utils
import xsd_simple_type


def xsd_list(attrs, parent, factory, schema_path, all_schemata):
    item_name = factory.get_attribute(attrs, 'itemType', default=None)
    item_name = factory.parse_qname(item_name)

    new_element = XsdList(item_name, parent_schema=all_schemata[schema_path])
    parent.children.append(new_element)

    return (new_element, {
        'annotation': factory.noop_handler,
        'simpleType': xsd_simple_type.xsd_simpleType,
    })


class XsdList(base.XsdBase):
    def __init__(self, item_name, parent_schema=None):
        super(XsdList, self).__init__()

        self.item_name = item_name
        self.parent_schema = parent_schema

    @method_once
    def finalize(self, factory):
        item_type = None
        if self.item_name is None:
            for t in self.children:
                assert (isinstance(t, xsd_simple_type.XsdSimpleType) and
                        item_type is None), \
                    'Wrong content of List'

                item_type = t.finalize(factory)
        else:
            item_type = factory.resolve_simple_type(self.item_name,
                                                    self.parent_schema)

        return item_type

    def dump(self, context):
        with utils.XsdTagGuard('list', context):
            context.add_attribute('itemType', self.item_name)
