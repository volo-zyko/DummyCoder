# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import function_once

import base
import model
import uses


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
    return {x: base.NativeType(xsd_schema(), x)
            for x in _NATIVE_XSD_TYPE_NAMES}


@function_once
def xsd_schema():
    return model.Schema(XSD_NAMESPACE, 'xsd')


@function_once
def ct_urtype():
    seqpart = uses.Particle(False, 1, 1, model.Sequence())
    seqpart.term.members.append(
        uses.Particle(False, 1, base.UNBOUNDED, model.Any([], None)))

    root_seqpart = uses.Particle(False, 1, 1, model.Sequence())
    root_seqpart.term.members.append(
        uses.AttributeUse(None, False, False, False, model.Any([], None)))
    root_seqpart.term.members.append(seqpart)
    root_seqpart.term.members.append(
        uses.SchemaText(xsd_builtin_types()['string']))

    urtype = model.ComplexType('anyType', xsd_schema())
    urtype.structure = root_seqpart
    return urtype


@function_once
def st_urtype():
    urtype = model.SimpleType('anySimpleType', xsd_schema())

    restr = model.Restriction()
    restr.base = ct_urtype()
    urtype.restriction = restr

    return urtype
