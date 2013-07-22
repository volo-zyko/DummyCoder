# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.all
import dumco.schema.any
import dumco.schema.attribute
import dumco.schema.base
import dumco.schema.choice
import dumco.schema.complex_type
import dumco.schema.element
import dumco.schema.restriction
import dumco.schema.schema
import dumco.schema.sequence
import dumco.schema.simple_type

import dumco.schema.prv.attribute_group
import dumco.schema.prv.complex_content
import dumco.schema.prv.enumeration
import dumco.schema.prv.extension_cc
import dumco.schema.prv.extension_sc
import dumco.schema.prv.group
import dumco.schema.prv.list
import dumco.schema.prv.simple_content
import dumco.schema.prv.union


# Constants.
XML_NAMESPACE = 'http://www.w3.org/XML/1998/namespace'
XSD_NAMESPACE = 'http://www.w3.org/2001/XMLSchema'


# General checks.
def is_xsd_namespace(uri):
    return uri == XSD_NAMESPACE


# Type checks.
def has_complex_content(xsdtype):
    return (is_complex_type(xsdtype) and
            xsdtype.term is not None and xsdtype.text is None)


def has_simple_content(xsdtype):
    return (is_complex_type(xsdtype) and
            xsdtype.term is None and xsdtype.text is not None)


def is_native_type(xsdtype):
    return isinstance(xsdtype, dumco.schema.base.XsdNativeType)


def is_complex_type(xsdtype):
    return isinstance(xsdtype, dumco.schema.complex_type.ComplexType)


def is_complex_urtype(xsdtype):
    return (is_complex_type(xsdtype) and xsdtype.schema is None and
            xsdtype.name == 'anyType')


def is_primitive_type(xsdtype):
    return (is_native_type(xsdtype) or is_simple_type(xsdtype))


def is_restriction_type(xsdtype):
    return (is_simple_type(xsdtype) and xsdtype.restriction is not None)


def is_simple_type(xsdtype):
    return isinstance(xsdtype, dumco.schema.simple_type.SimpleType)


def is_simple_urtype(xsdtype):
    return (is_simple_type(xsdtype) and xsdtype.schema is None and
            xsdtype.name == 'anySimpleType')


def is_union_type(xsdtype):
    return (is_simple_type(xsdtype) and xsdtype.union)


# Element checks.
def is_all(xsdAll):
    return isinstance(xsdAll, dumco.schema.all.All)


def is_any(xsdAny):
    return isinstance(xsdAny, dumco.schema.any.Any)


def is_attribute(attr):
    return isinstance(attr, dumco.schema.attribute.Attribute)


def is_attribute_use(attr):
    return isinstance(attr, dumco.schema.uses.AttributeUse)


def is_choice(choice):
    return isinstance(choice, dumco.schema.choice.Choice)


def is_compositor(compositor):
    return (is_sequence(compositor) or is_choice(compositor) or
            is_all(compositor))


def is_element(element):
    return isinstance(element, dumco.schema.element.Element)


def is_particle(xsdtype):
    return isinstance(xsdtype, dumco.schema.uses.Particle)


def is_sequence(sequence):
    return isinstance(sequence, dumco.schema.sequence.Sequence)


def is_schema(schema):
    return isinstance(schema, dumco.schema.schema.Schema)


def is_xmlattribute(xsdtype):
    return isinstance(xsdtype, dumco.schema.base.XmlAttribute)
