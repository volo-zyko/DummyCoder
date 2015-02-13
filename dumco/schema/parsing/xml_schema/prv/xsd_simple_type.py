# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.base
import dumco.schema.checks
import dumco.schema.model
import dumco.schema.uses

import base
import xsd_list
import xsd_restriction
import xsd_union


def xsd_simpleType(attrs, parent_element, factory, schema_path, all_schemata):
    new_element = XsdSimpleType(attrs, all_schemata[schema_path])
    parent_element.children.append(new_element)

    factory.add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                                 'simple_types', is_type=True)

    return (new_element, {
        'annotation': factory.noop_handler,
        'list': xsd_list.xsd_list,
        'restriction': xsd_restriction.xsd_restriction,
        'union': xsd_union.xsd_union,
    })


class XsdSimpleType(base.XsdBase):
    def __init__(self, attrs, parent_schema):
        super(XsdSimpleType, self).__init__(attrs)

        self.schema_element = dumco.schema.model.SimpleType(
            self.attr('name'), parent_schema.schema_element)

    @method_once
    def finalize(self, factory):
        for c in self.children:
            assert (isinstance(c, xsd_restriction.XsdRestriction) or
                    isinstance(c, xsd_list.XsdList) or
                    isinstance(c, xsd_union.XsdUnion)), \
                'Wrong content of SimpleType'

            if isinstance(c, xsd_restriction.XsdRestriction):
                restriction_or_type = c.finalize(factory)
                if dumco.schema.checks.is_restriction(restriction_or_type):
                    self.schema_element.restriction = restriction_or_type
                else:
                    self.schema_element = restriction_or_type
            elif isinstance(c, xsd_list.XsdList):
                listitem = dumco.schema.uses.ListTypeCardinality(
                    c.finalize(factory).itemtype,
                    0, dumco.schema.base.UNBOUNDED)
                self.schema_element.listitems.append(listitem)
            elif isinstance(c, xsd_union.XsdUnion):
                self.schema_element.union = c.finalize(factory).membertypes

        assert ((self.schema_element.restriction is not None and
                 self.schema_element.listitems == [] and
                 self.schema_element.union == []) or
                (self.schema_element.listitems != [] and
                 self.schema_element.restriction is None and
                 self.schema_element.union == []) or
                (self.schema_element.union != [] and
                 self.schema_element.listitems == [] and
                 self.schema_element.restriction is None)), \
            'SimpleType must be any of restriction, list, union'

        return eliminate_degenerate_simple_type(self.schema_element)


def eliminate_degenerate_simple_type(st):
    if (dumco.schema.checks.is_restriction_type(st) and
            not st.restriction.enumerations and
            st.restriction.fraction_digits is None and
            st.restriction.length is None and
            st.restriction.max_exclusive is None and
            st.restriction.max_inclusive is None and
            st.restriction.max_length is None and
            st.restriction.min_exclusive is None and
            st.restriction.min_inclusive is None and
            st.restriction.min_length is None and
            not st.restriction.patterns and
            st.restriction.total_digits is None and
            st.restriction.white_space is None):
        return st.restriction.base

    return st
