# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.checks


def restrict_base_attributes(base, factory, prohibited, redefined):
    # Utility function common for XsdSimpleRestriction and
    # XsdComplexRestriction which adds attribute uses only if they are not
    # restricted by derived type.
    def is_attr_in_list(attr, attrlist):
        return any([attr.name == x.attribute.name for x in attrlist])

    res_attr_uses = []
    for u in base.attribute_uses():
        if (not dumco.schema.checks.is_any(u.attribute) and
                (is_attr_in_list(u.attribute, prohibited) or
                 is_attr_in_list(u.attribute, redefined))):
            continue

        res_attr_uses.append(u)

    return res_attr_uses
