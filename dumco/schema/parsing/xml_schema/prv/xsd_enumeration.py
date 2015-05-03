# Distributed under the GPLv2 License; see accompanying file COPYING.

import base
import utils


def xsd_enumeration(attrs, parent, builder, schema_path, all_schemata):
    new_element = XsdEnumeration(builder.get_attribute(attrs, 'value'))
    parent.children.append(new_element)

    return (new_element, {
        'annotation': builder.xsd_annotation,
    })


class XsdEnumeration(base.XsdBase):
    def __init__(self, value):
        super(XsdEnumeration, self).__init__()

        self.value = value

    def dump(self, context):
        with utils.XsdTagGuard('enumeration', context):
            context.add_attribute('value', self.value)
