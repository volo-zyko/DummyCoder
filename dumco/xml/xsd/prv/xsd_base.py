# Distributed under the GPLv2 License; see accompanying file COPYING.

import sys

import dumco.schema.checks


class XsdBase(object):
    def __init__(self, attrs):
        self.attrs = {x[1]: v for (x,v) in attrs.items()}
        self.children = []

    def attr(self, name):
        return self.attrs.get(name, None)

    def __setattr__(self, name, value):
        if name not in self.__dict__:
            tb = sys._current_frames().values()[0]
            assert tb.f_back.f_code.co_name == '__init__', \
                'Setting non-existent attribute'
        self.__dict__[name] = value


def restrict_base_attributes(base, prohibited_attrs, redefined_attrs,
                             attributes, schema, factory):
    is_attr_in_list = lambda attr, attrlist: any(
        map(lambda x: attr.name == x.attribute.name and
                      attr.schema.target_ns == x.attribute.schema.target_ns,
            attrlist))
    for a in base.attributes:
        if (not dumco.schema.checks.is_any(a.attribute) and
            (is_attr_in_list(a.attribute, prohibited_attrs) or
             is_attr_in_list(a.attribute, redefined_attrs))):
            continue

        attributes.append(a)

        factory.fix_imports(schema, a.attribute)
