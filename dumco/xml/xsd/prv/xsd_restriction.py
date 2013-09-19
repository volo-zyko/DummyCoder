# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.checks
import dumco.schema.elements

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
            dumco.schema.elements.Restriction(parent_schema.schema_element)

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
                    self.schema_element.enumeration.append(
                        (t.value, t.schema_element.doc))
        elif self.schema_element.base is None:
            base = factory.resolve_simple_type(self.attr('base'),
                                               self.schema, finalize=True)
            for x in self.children:
                assert isinstance(x, xsd_enumeration.XsdEnumeration), \
                    'Expected only Enumerations'
                self.schema_element.enumeration.append(
                    (x.value, x.schema_element.doc))
        else:
            base = self.schema_element.base

            for t in self.children:
                if isinstance(t, xsd_enumeration.XsdEnumeration):
                    self.schema_element.enumeration.append(
                        (t.value, t.schema_element.doc))

        self.schema_element.base = self._merge_base_restriction(base)

        return self.schema_element

    def _merge_base_restriction(self, base):
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

            base = self._merge_base_restriction(base.restriction.base)

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

    xsd_fractionDigits = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdRestriction._value_handler('fraction_digits', attrs,
            parent_element, factory, schema_path, all_schemata)

    xsd_length = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdRestriction._value_handler('length', attrs,
            parent_element, factory, schema_path, all_schemata)

    xsd_maxExclusive = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdRestriction._value_handler('max_exclusive', attrs,
            parent_element, factory, schema_path, all_schemata)

    xsd_maxInclusive = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdRestriction._value_handler('max_inclusive', attrs,
            parent_element, factory, schema_path, all_schemata)

    xsd_maxLength = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdRestriction._value_handler('max_length', attrs,
            parent_element, factory, schema_path, all_schemata)

    xsd_minExclusive = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdRestriction._value_handler('min_exclusive', attrs,
            parent_element, factory, schema_path, all_schemata)

    xsd_minInclusive = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdRestriction._value_handler('min_inclusive', attrs,
            parent_element, factory, schema_path, all_schemata)

    xsd_minLength = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdRestriction._value_handler('min_length', attrs,
            parent_element, factory, schema_path, all_schemata)

    xsd_pattern = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdRestriction._value_handler('pattern', attrs,
            parent_element, factory, schema_path, all_schemata)

    xsd_totalDigits = lambda _x, attrs, parent_element, factory, schema_path, \
        all_schemata: XsdRestriction._value_handler('total_digits', attrs,
            parent_element, factory, schema_path, all_schemata)

    @staticmethod
    def xsd_whiteSpace(attrs, parent_element, factory,
                       schema_path, all_schemata):
        assert hasattr(parent_element.schema_element, 'white_space')

        value = factory.get_attribute(attrs, 'value')
        if value == 'preserve':
            parent_element.schema_element.white_space = \
                dumco.schema.elements.Restriction.WS_PRESERVE
        elif value == 'replace':
            parent_element.schema_element.white_space = \
                dumco.schema.elements.Restriction.WS_REPLACE
        elif value == 'collapse':
            parent_element.schema_element.white_space = \
                dumco.schema.elements.Restriction.WS_COLLAPSE
        else: # pragma: no cover
            assert False

        return (parent_element, {
            'annotation': factory.noop_handler,
        })
