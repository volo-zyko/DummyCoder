# Distributed under the GPLv2 License; see accompanying file COPYING.

import collections
import sys

from dumco.utils.decorators import function_once


# Constants.
XML_NAMESPACE = 'http://www.w3.org/XML/1998/namespace'
XML_XSD_URI = 'http://www.w3.org/2001/xml.xsd'
XSD_NAMESPACE = 'http://www.w3.org/2001/XMLSchema'

UNBOUNDED = sys.maxsize

_NATIVE_XSD_TYPE_NAMES = [
    # Base
    'string',
    'boolean',
    'decimal',
    'float',
    'double',
    'hexBinary',
    'base64Binary',
    'anyURI',
    'QName',
    'NOTATION',
    # Time related
    'duration',
    'dateTime',
    'time',
    'date',
    'gYearMonth',
    'gYear',
    'gMonthDay',
    'gDay',
    'gMonth',
    # Derived
    'normalizedString',
    'token',
    'language',
    'NMTOKEN',
    'NMTOKENS',
    'Name',
    'NCName',
    'ID',
    'IDREF',
    'IDREFS',
    'ENTITY',
    'ENTITIES',
    'integer',
    'nonPositiveInteger',
    'negativeInteger',
    'long',
    'int',
    'short',
    'byte',
    'nonNegativeInteger',
    'unsignedLong',
    'unsignedInt',
    'unsignedShort',
    'unsignedByte',
    'positiveInteger',
]


@function_once
def xsd_builtin_types():
    return {x: XsdNativeType(x) for x in _NATIVE_XSD_TYPE_NAMES}


@function_once
def xml_attributes():
    attrs = {x: XmlAttribute(x) for x in ['base', 'id', 'lang', 'space']}
    attrs['space'].constraint = AttributeValueConstraint(None, 'preserve')
    return attrs


class SchemaBase(object):
    def __init__(self, parent_schema):
        self.schema = parent_schema
        self._docs = []

    def append_doc(self, doc):
        d = doc.strip()
        if d != '':
            self._docs.append(d)

    @property
    def doc(self):
        return ' '.join(self._docs)

    def __setattr__(self, name, value):
        if name not in self.__dict__:
            tb = sys._current_frames().values()[0]
            assert tb.f_back.f_code.co_name == '__init__', \
                'Setting non-existent attribute'
        self.__dict__[name] = value


class XsdNativeType(SchemaBase):
    def __init__(self, name):
        super(XsdNativeType, self).__init__(None)

        self.name = name


class SchemaText(SchemaBase):
    def __init__(self, simple_type):
        super(SchemaText, self).__init__(None)

        self.name = 'text()'
        self.type = simple_type


AttributeValueConstraint = collections.namedtuple('AttributeValueConstraint',
                                                  ['fixed', 'default'])


class XmlAttribute(SchemaBase):
    def __init__(self, name):
        super(XmlAttribute, self).__init__(None)

        self.name = name
        self.constraint = AttributeValueConstraint(False, None)
