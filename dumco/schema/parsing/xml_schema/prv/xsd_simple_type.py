# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.base
import dumco.schema.checks
import dumco.schema.model
import dumco.schema.uses

import base
import utils
import xsd_list
import xsd_restriction
import xsd_union


def xsd_simpleType(attrs, parent, builder, schema_path, all_schemata):
    name = builder.get_attribute(attrs, 'name', default=None)

    new_element = XsdSimpleType(name,
                                all_schemata[schema_path])
    parent.children.append(new_element)

    builder.add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                                 'simple_types', is_type=True)

    return (new_element, {
        'annotation': builder.noop_handler,
        'list': xsd_list.xsd_list,
        'restriction': xsd_restriction.xsd_restriction,
        'union': xsd_union.xsd_union,
    })


class XsdSimpleType(base.XsdBase):
    def __init__(self, name, parent_schema=None):
        super(XsdSimpleType, self).__init__()

        self.name = name
        self.parent_schema = parent_schema

    @method_once
    def finalize(self, builder):
        simple_type = dumco.schema.model.SimpleType(
            self.name, self.parent_schema.dom_element)

        for c in self.children:
            assert (isinstance(c, xsd_restriction.XsdRestriction) or
                    isinstance(c, xsd_list.XsdList) or
                    isinstance(c, xsd_union.XsdUnion)), \
                'Wrong content of SimpleType'

            if isinstance(c, xsd_restriction.XsdRestriction):
                restriction_or_type = c.finalize(builder)
                if dumco.schema.checks.is_restriction(restriction_or_type):
                    simple_type.restriction = restriction_or_type
                else:
                    simple_type = restriction_or_type
            elif isinstance(c, xsd_list.XsdList):
                listitem = dumco.schema.uses.ListTypeCardinality(
                    c.finalize(builder), 0, dumco.schema.base.UNBOUNDED)
                simple_type.listitems.append(listitem)
            elif isinstance(c, xsd_union.XsdUnion):
                simple_type.union = c.finalize(builder)

        assert ((simple_type.restriction is not None and
                 simple_type.listitems == [] and
                 simple_type.union == []) or
                (simple_type.listitems != [] and
                 simple_type.restriction is None and
                 simple_type.union == []) or
                (simple_type.union != [] and
                 simple_type.listitems == [] and
                 simple_type.restriction is None)), \
            'SimpleType must be any of restriction, list, union'

        return utils.eliminate_degenerate_simple_type(simple_type)

    def dump(self, context):
        with utils.XsdTagGuard('simpleType', context):
            context.add_attribute('name', self.name)

            for c in self.children:
                c.dump(context)
