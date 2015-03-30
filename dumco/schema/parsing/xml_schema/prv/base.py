# Distributed under the GPLv2 License; see accompanying file COPYING.

import sys

import dumco.schema.model


class XsdBase(object):
    def __init__(self):
        self.text = []
        self.children = []

    def __setattr__(self, name, value):
        if name not in self.__dict__:
            tb = sys._current_frames().values()[0]
            assert (tb.f_back.f_code.co_name == '__init__' or
                    tb.f_back.f_code.co_filename.endswith('decorators.py')), \
                'Setting non-existent attribute'
        self.__dict__[name] = value

    def dump(self, context):
        assert False, 'Implement dump method in derived classes'


class XsdRestrictionBase(XsdBase):
    @staticmethod
    def _value_handler(fieldname, attrs, parent, factory,
                       schema_path, all_schemata):
        assert hasattr(parent.dom_element, fieldname)
        setattr(parent.dom_element, fieldname,
                factory.get_attribute(attrs, 'value'))

        return (parent, {
            'annotation': factory.noop_handler,
        })

    @staticmethod
    def xsd_fractionDigits(attrs, parent, factory,
                           schema_path, all_schemata):
        return XsdRestrictionBase._value_handler(
            'fraction_digits', attrs, parent,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_length(attrs, parent, factory,
                   schema_path, all_schemata):
        return XsdRestrictionBase._value_handler(
            'length', attrs, parent,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_maxExclusive(attrs, parent, factory,
                         schema_path, all_schemata):
        return XsdRestrictionBase._value_handler(
            'max_exclusive', attrs, parent,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_maxInclusive(attrs, parent, factory,
                         schema_path, all_schemata):
        return XsdRestrictionBase._value_handler(
            'max_inclusive', attrs, parent,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_maxLength(attrs, parent, factory,
                      schema_path, all_schemata):
        return XsdRestrictionBase._value_handler(
            'max_length', attrs, parent,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_minExclusive(attrs, parent, factory,
                         schema_path, all_schemata):
        return XsdRestrictionBase._value_handler(
            'min_exclusive', attrs, parent,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_minInclusive(attrs, parent, factory,
                         schema_path, all_schemata):
        return XsdRestrictionBase._value_handler(
            'min_inclusive', attrs, parent,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_minLength(attrs, parent, factory,
                      schema_path, all_schemata):
        return XsdRestrictionBase._value_handler(
            'min_length', attrs, parent,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_pattern(attrs, parent, factory,
                    schema_path, all_schemata):
        parent.dom_element.patterns.append(
            factory.get_attribute(attrs, 'value'))

        return (parent, {
            'annotation': factory.noop_handler,
        })

    @staticmethod
    def xsd_totalDigits(attrs, parent, factory,
                        schema_path, all_schemata):
        return XsdRestrictionBase._value_handler(
            'total_digits', attrs, parent,
            factory, schema_path, all_schemata)

    @staticmethod
    def xsd_whiteSpace(attrs, parent, factory,
                       schema_path, all_schemata):
        assert hasattr(parent.dom_element, 'white_space')

        value = factory.get_attribute(attrs, 'value')
        if value == 'preserve':
            parent.dom_element.white_space = \
                dumco.schema.model.Restriction.WS_PRESERVE
        elif value == 'replace':
            parent.dom_element.white_space = \
                dumco.schema.model.Restriction.WS_REPLACE
        elif value == 'collapse':
            parent.dom_element.white_space = \
                dumco.schema.model.Restriction.WS_COLLAPSE
        else:  # pragma: no cover
            assert False, 'Unknown token for whiteSpace'

        return (parent, {
            'annotation': factory.noop_handler,
        })
