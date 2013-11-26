# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import function_once

import base


# Constants.
XSD_NAMESPACE = 'http://www.w3.org/2001/XMLSchema'
XSD_DATATYPES_NAMESPACE = 'http://www.w3.org/2001/XMLSchema-datatypes'
XML_XSD_URI = 'http://www.w3.org/2001/xml.xsd'

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
    return {x: base.NativeType(XSD_NAMESPACE, x)
            for x in _NATIVE_XSD_TYPE_NAMES}


