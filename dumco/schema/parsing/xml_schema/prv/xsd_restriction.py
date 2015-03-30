# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.checks
import dumco.schema.model
import dumco.schema.uses

import base
import utils
import xsd_enumeration
import xsd_simple_type


def xsd_restriction(attrs, parent, factory, schema_path, all_schemata):
    base_name = factory.get_attribute(attrs, 'base', default=None)
    base_name = factory.parse_qname(base_name)

    restriction = dumco.schema.model.Restriction()

    new_element = XsdRestriction(restriction, base_name,
                                 parent_schema=all_schemata[schema_path])
    parent.children.append(new_element)

    return (new_element, {
        'annotation': factory.noop_handler,
        'enumeration': xsd_enumeration.xsd_enumeration,
        'fractionDigits': new_element.xsd_fractionDigits,
        'length': new_element.xsd_length,
        'maxExclusive': new_element.xsd_maxExclusive,
        'maxInclusive': new_element.xsd_maxInclusive,
        'maxLength': new_element.xsd_maxLength,
        'minExclusive': new_element.xsd_minExclusive,
        'minInclusive': new_element.xsd_minInclusive,
        'minLength': new_element.xsd_minLength,
        'pattern': new_element.xsd_pattern,
        'simpleType': xsd_simple_type.xsd_simpleType,
        'totalDigits': new_element.xsd_totalDigits,
        'whiteSpace': new_element.xsd_whiteSpace,
    })


class XsdRestriction(base.XsdRestrictionBase):
    def __init__(self, restriction, base_name, parent_schema=None):
        super(XsdRestriction, self).__init__()

        self.dom_element = restriction
        self.base_name = base_name
        self.parent_schema = parent_schema

    @method_once
    def finalize(self, factory):
        base_type = None
        if self.base_name is None:
            for t in self.children:
                assert ((isinstance(t, xsd_simple_type.XsdSimpleType) or
                         isinstance(t, xsd_enumeration.XsdEnumeration)) and
                        base_type is None), \
                    'Wrong content of Restriction'

                if isinstance(t, xsd_simple_type.XsdSimpleType):
                    base_type = t.finalize(factory)
                elif isinstance(t, xsd_enumeration.XsdEnumeration):
                    enum = dumco.schema.model.EnumerationValue(t.value,
                                                               ' '.join(t.text))
                    self.dom_element.enumerations.append(enum)
        else:
            base_type = factory.resolve_simple_type(self.base_name,
                                                    self.parent_schema)
            for x in self.children:
                assert isinstance(x, xsd_enumeration.XsdEnumeration), \
                    'Expected only Enumerations'

                enum = dumco.schema.model.EnumerationValue(x.value,
                                                           ' '.join(x.text))
                self.dom_element.enumerations.append(enum)

        assert base_type is not None, 'Restriction does not have base type'

        return utils.connect_restriction_base(self.dom_element, base_type)

    def dump(self, context):
        with utils.XsdTagGuard('restriction', context):
            context.add_attribute('base', self.item_name)

            for c in self.children:
                c.dump(context)
