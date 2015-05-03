# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import utils
import xsd_extension_sc
import xsd_restriction_sc


def xsd_simpleContent(attrs, parent, builder, schema_path, all_schemata):
    new_element = XsdSimpleContent()
    parent.children.append(new_element)

    return (new_element, {
        'annotation': builder.noop_handler,
        'extension': xsd_extension_sc.xsd_extension,
        'restriction': xsd_restriction_sc.xsd_restriction,
    })


class XsdSimpleContent(base.XsdBase):
    @method_once
    def finalize(self, builder):
        content_type = None
        attr_uses = []

        for c in self.children:
            assert ((isinstance(c, xsd_extension_sc.XsdSimpleExtension) or
                     isinstance(c, xsd_restriction_sc.XsdSimpleRestriction)) and
                    content_type is None and not attr_uses), \
                'Wrong content of SimpleContent'

            (content_type, attr_uses) = c.finalize(builder)

        return (content_type, attr_uses)

    def dump(self, context):
        with utils.XsdTagGuard('simpleContent', context):
            for c in self.children:
                c.dump(context)
