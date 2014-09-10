# Distributed under the GPLv2 License; see accompanying file COPYING.

import sys

import dumco.schema.checks


class XsdBase(object):
    def __init__(self, attrs):
        self.attrs = attrs
        self.children = []

    def attr(self, name):
        return self.attrs.get(name, None)

    def __setattr__(self, name, value):
        if name not in self.__dict__:
            tb = sys._current_frames().values()[0]
            assert (tb.f_back.f_code.co_name == '__init__' or
                    tb.f_back.f_code.co_filename.endswith('decorators.py')), \
                'Setting non-existent attribute'
        self.__dict__[name] = value


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
