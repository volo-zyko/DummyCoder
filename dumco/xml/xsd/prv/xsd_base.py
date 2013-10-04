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
            assert tb.f_back.f_code.co_name == '__init__', \
                'Setting non-existent attribute'
        self.__dict__[name] = value


def restrict_base_attributes(base, attr_uses, factory,
                             prohibited_attr_uses, redefined_attr_uses):
    # Utility function common for XsdSimpleRestriction and XsdComplexRestriction
    # which adds attribute uses only if they are not restricted by derived
    # type.
    is_attr_in_list = lambda attr, attrlist: any(
        map(lambda x: attr.name == x.attribute.name and
                      attr.schema == x.attribute.schema,
            attrlist))
    for u in base.attribute_uses:
        if (not dumco.schema.checks.is_any(u.attribute) and
            (is_attr_in_list(u.attribute, prohibited_attr_uses) or
             is_attr_in_list(u.attribute, redefined_attr_uses))):
            continue

        attr_uses.append(u)
