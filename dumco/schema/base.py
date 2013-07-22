# Distributed under the GPLv2 License; see accompanying file COPYING.

import sys

from dumco.utils.decorators import method_once


UNBOUNDED = sys.maxsize


class SchemaBase(object):
    def __init__(self, attrs, parent_schema):
        self.attrs = {x[1]: v for (x,v) in attrs.items()}
        self.children = []
        self.schema = parent_schema
        self._docs = []

    def attr(self, name):
        return self.attrs.get(name, None)

    def append_doc(self, doc):
        d = doc.strip()
        if d != '':
            self._docs.append(d)

    @property
    def doc(self):
        return ' '.join(self._docs)

    @method_once
    def finalize(self, fakefactory):
        delattr(self, 'attrs')
        delattr(self, 'children')
        return self


class XsdNativeType(SchemaBase):
    def __init__(self, name):
        super(XsdNativeType, self).__init__({}, None)

        self.name = name
        super(XsdNativeType, self).finalize(None)


class SchemaText(SchemaBase):
    def __init__(self, simple_type):
        super(SchemaText, self).__init__({}, None)

        self.name = 'text()'
        self.type = simple_type
        super(SchemaText, self).finalize(None)


class XmlAttribute(SchemaBase):
    def __init__(self, name):
        super(XmlAttribute, self).__init__({}, None)

        self.name = name
        super(XmlAttribute, self).finalize(None)


NATIVE_XSD_TYPE_NAMES = [
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
