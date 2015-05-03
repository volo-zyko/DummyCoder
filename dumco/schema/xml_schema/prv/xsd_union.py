# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.checks

import base
import utils
import xsd_simple_type


def xsd_union(attrs, parent, builder, schema_path, all_schemata):
    member_names = builder.get_attribute(attrs, 'memberTypes', default='')
    member_names = [builder.parse_qname(q) for q in member_names.split()]

    new_element = XsdUnion(member_names,
                           parent_schema=all_schemata[schema_path])
    parent.children.append(new_element)

    return (new_element, {
        'annotation': builder.noop_handler,
        'simpleType': xsd_simple_type.xsd_simpleType,
    })


class XsdUnion(base.XsdBase):
    def __init__(self, member_names, parent_schema=None):
        super(XsdUnion, self).__init__()

        self.member_names = member_names
        self.parent_schema = parent_schema

    @method_once
    def finalize(self, builder):
        member_types = []

        for t in self.member_names:
            member_type = builder.resolve_simple_type(t, self.parent_schema)
            self._merge_unions(member_type, member_types)

        for t in self.children:
            assert isinstance(t, xsd_simple_type.XsdSimpleType), \
                'Wrong content of Union'

            member_type = t.finalize(builder)
            self._merge_unions(member_type, member_types)

        assert member_types, 'No member types in Union'

        return member_types

    def dump(self, context):
        with utils.XsdTagGuard('union', context):
            context.add_attribute('memberTypes', self.member_names)

    def _merge_unions(self, member, member_types):
        if dumco.schema.checks.is_union_type(member):
            for member_type in member.union:
                self._merge_unions(member_type, member_types)
        elif member not in member_types:
            member_types.append(member)
