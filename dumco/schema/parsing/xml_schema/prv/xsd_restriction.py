# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.checks
import dumco.schema.model
import dumco.schema.uses

import xsd_base
import xsd_enumeration
import xsd_simple_type


def xsd_restriction(attrs, parent_element, factory, schema_path, all_schemata):
    new_element = XsdRestriction(attrs, all_schemata[schema_path])
    parent_element.children.append(new_element)

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


class XsdRestriction(xsd_base.XsdBase):
    def __init__(self, attrs, parent_schema):
        super(XsdRestriction, self).__init__(attrs)

        self.schema = parent_schema
        self.schema_element = \
            dumco.schema.model.Restriction(parent_schema.schema_element)

    @method_once
    def finalize(self, factory):
        base = None
        if self.attr('base') is None:
            for t in self.children:
                assert ((isinstance(t, xsd_simple_type.XsdSimpleType) or
                         isinstance(t, xsd_enumeration.XsdEnumeration)) and
                        base is None), \
                    'Wrong content of Restriction'

                if isinstance(t, xsd_simple_type.XsdSimpleType):
                    base = t.finalize(factory)
                elif isinstance(t, xsd_enumeration.XsdEnumeration):
                    enum = dumco.schema.model.EnumerationValue(
                        t.value, t.schema_element.doc)
                    self.schema_element.enumerations.append(enum)
        else:
            base = factory.resolve_simple_type(self.attr('base'),
                                               self.schema, finalize=True)
            for x in self.children:
                assert isinstance(x, xsd_enumeration.XsdEnumeration), \
                    'Expected only Enumerations'
                enum = dumco.schema.model.EnumerationValue(
                    x.value, x.schema_element.doc)
                self.schema_element.enumerations.append(enum)

        assert base is not None, 'Restriction does not have base type'

        if dumco.schema.checks.is_list_type(base):
            itemtype = base.listitems[0]

            min_occurs = itemtype.min_occurs
            max_occurs = itemtype.max_occurs
            if self.schema_element.length is not None:
                min_occurs = self.schema_element.length
                max_occurs = self.schema_element.length
            else:
                if self.schema_element.min_length is not None:
                    min_occurs = self.schema_element.min_length
                elif self.schema_element.max_length is not None:
                    max_occurs = self.schema_element.max_length

            base.listitems[0] = dumco.schema.uses.ListTypeCardinality(
                itemtype, min_occurs, max_occurs)

            return base
        else:
            self.schema_element.base = self.merge_base_restriction(base)

            return self.schema_element

    def merge_base_restriction(self, base):
        def merge(attr):
            if not getattr(self.schema_element, attr):
                value = getattr(base.restriction, attr)
                if not value:
                    setattr(self.schema_element, attr, value)

        if dumco.schema.checks.is_restriction_type(base):
            merge('enumeration')
            merge('fraction_digits')
            merge('length')
            merge('max_exclusive')
            merge('max_inclusive')
            merge('max_length')
            merge('min_exclusive')
            merge('min_inclusive')
            merge('min_length')
            merge('pattern')
            merge('total_digits')
            merge('white_space')

            base = self.merge_base_restriction(base.restriction.base)

        return base

    @staticmethod
    def _value_handler(fieldname, attrs, parent_element, factory,
                       schema_path, all_schemata):
        assert hasattr(parent_element.schema_element, fieldname)
        setattr(parent_element.schema_element, fieldname,
                factory.get_attribute(attrs, 'value'))

        return (parent_element, {
            'annotation': factory.noop_handler,
        })

    @staticmethod
    def xsd_fractionDigits(attrs, parent_element, factory,
                           schema_path, all_schemata):
        return XsdRestriction._value_handler(
            'fraction_digits', attrs, parent_element,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_length(attrs, parent_element, factory,
                   schema_path, all_schemata):
        return XsdRestriction._value_handler(
            'length', attrs, parent_element,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_maxExclusive(attrs, parent_element, factory,
                         schema_path, all_schemata):
        return XsdRestriction._value_handler(
            'max_exclusive', attrs, parent_element,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_maxInclusive(attrs, parent_element, factory,
                         schema_path, all_schemata):
        return XsdRestriction._value_handler(
            'max_inclusive', attrs, parent_element,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_maxLength(attrs, parent_element, factory,
                      schema_path, all_schemata):
        return XsdRestriction._value_handler(
            'max_length', attrs, parent_element,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_minExclusive(attrs, parent_element, factory,
                         schema_path, all_schemata):
        return XsdRestriction._value_handler(
            'min_exclusive', attrs, parent_element,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_minInclusive(attrs, parent_element, factory,
                         schema_path, all_schemata):
        return XsdRestriction._value_handler(
            'min_inclusive', attrs, parent_element,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_minLength(attrs, parent_element, factory,
                      schema_path, all_schemata):
        return XsdRestriction._value_handler(
            'min_length', attrs, parent_element,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_pattern(attrs, parent_element, factory,
                    schema_path, all_schemata):
        parent_element.schema_element.patterns.append(
            factory.get_attribute(attrs, 'value'))

        return (parent_element, {
            'annotation': factory.noop_handler,
        })

    @staticmethod
    def xsd_totalDigits(attrs, parent_element, factory,
                        schema_path, all_schemata):
        return XsdRestriction._value_handler(
            'total_digits', attrs, parent_element,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_whiteSpace(attrs, parent_element, factory,
                       schema_path, all_schemata):
        assert hasattr(parent_element.schema_element, 'white_space')

        value = factory.get_attribute(attrs, 'value')
        if value == 'preserve':
            parent_element.schema_element.white_space = \
                dumco.schema.model.Restriction.WS_PRESERVE
        elif value == 'replace':
            parent_element.schema_element.white_space = \
                dumco.schema.model.Restriction.WS_REPLACE
        elif value == 'collapse':
            parent_element.schema_element.white_space = \
                dumco.schema.model.Restriction.WS_COLLAPSE
        else:  # pragma: no cover
            assert False, 'Unknown token for whiteSpace'

        return (parent_element, {
            'annotation': factory.noop_handler,
        })
