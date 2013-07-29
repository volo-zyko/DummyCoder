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
        'length': factory.xsd_length,
        'maxExclusive': factory.xsd_maxExclusive,
        'maxInclusive': factory.xsd_maxInclusive,
        'maxLength': factory.xsd_maxLength,
        'minExclusive': factory.xsd_minExclusive,
        'minInclusive': factory.xsd_minInclusive,
        'minLength': factory.xsd_minLength,
        'pattern': factory.xsd_pattern,
        'simpleType': xsd_simple_type.xsd_simpleType,
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

        self.schema_element.base = self._merge_base_restriction(base)

        return self.schema_element

    def _merge_base_restriction(self, base):
        def merge(attr):
            if not getattr(self.schema_element, attr):
                value = getattr(base.restriction, attr)
                setattr(self.schema_element, attr, value)

        if dumco.schema.checks.is_restriction_type(base):
            merge('enumeration')
            merge('length')
            merge('max_exclusive')
            merge('max_inclusive')
            merge('max_length')
            merge('min_exclusive')
            merge('min_inclusive')
            merge('min_length')
            merge('pattern')

            base = self._merge_base_restriction(base.restriction.base)

        return base
