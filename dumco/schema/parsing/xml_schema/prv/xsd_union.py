# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.checks

import base
import xsd_simple_type


def xsd_union(attrs, parent_element, factory, schema_path, all_schemata):
    new_element = XsdUnion(attrs, all_schemata[schema_path])
    parent_element.children.append(new_element)

    return (new_element, {
        'annotation': factory.noop_handler,
        'simpleType': xsd_simple_type.xsd_simpleType,
    })


class XsdUnion(base.XsdBase):
    def __init__(self, attrs, parent_schema):
        super(XsdUnion, self).__init__(attrs)

        self.schema = parent_schema
        self.membertypes = []

    @method_once
    def finalize(self, factory):
        if self.attr('memberTypes') is not None:
            for t in self.attr('memberTypes'):
                membertype = factory.resolve_simple_type(t, self.schema)
                self._merge_unions(membertype)

        for t in self.children:
            assert isinstance(t, xsd_simple_type.XsdSimpleType), \
                'Wrong content of Union'

            membertype = t.finalize(factory)
            self._merge_unions(membertype)

        assert self.membertypes, 'No member types in Union'

        return self

    def _merge_unions(self, member):
        if dumco.schema.checks.is_union_type(member):
            for membertype in member.union:
                self._merge_unions(membertype)
        elif member not in self.membertypes:
            self.membertypes.append(member)
