# Distributed under the GPLv2 License; see accompanying file COPYING.

import base
import elements
import uses


# Constants.
XML_NAMESPACE = 'http://www.w3.org/XML/1998/namespace'
XSD_NAMESPACE = 'http://www.w3.org/2001/XMLSchema'


# General checks.
def is_xsd_namespace(uri):
    return uri == XSD_NAMESPACE


# Type checks.
def has_complex_content(xsdtype):
    return (is_complex_type(xsdtype) and
            xsdtype.particle is not None and xsdtype.text is None)


def has_simple_content(xsdtype):
    return (is_complex_type(xsdtype) and
            xsdtype.particle is None and xsdtype.text is not None)


def is_native_type(xsdtype):
    return isinstance(xsdtype, base.XsdNativeType)


def is_complex_type(xsdtype):
    return isinstance(xsdtype, elements.ComplexType)


def is_complex_urtype(xsdtype):
    return (is_complex_type(xsdtype) and xsdtype.schema is None and
            xsdtype.name == 'anyType')


def is_list_type(xsdtype):
    return (is_simple_type(xsdtype) and xsdtype.listitem is not None)


def is_primitive_type(xsdtype):
    return (is_native_type(xsdtype) or is_simple_type(xsdtype))


def is_restriction_type(xsdtype):
    return (is_simple_type(xsdtype) and xsdtype.restriction is not None)


def is_simple_type(xsdtype):
    return isinstance(xsdtype, elements.SimpleType)


def is_simple_urtype(xsdtype):
    return (is_simple_type(xsdtype) and xsdtype.schema is None and
            xsdtype.name == 'anySimpleType')


def is_union_type(xsdtype):
    return (is_simple_type(xsdtype) and xsdtype.union)


# Element checks.
def is_all(xsdAll):
    return isinstance(xsdAll, elements.All)


def is_any(xsdAny):
    return isinstance(xsdAny, elements.Any)


def is_attribute(attr):
    return isinstance(attr, elements.Attribute)


def is_attribute_use(attr):
    return isinstance(attr, uses.AttributeUse)


def is_choice(choice):
    return isinstance(choice, elements.Choice)


def is_compositor(compositor):
    return (is_sequence(compositor) or is_choice(compositor) or
            is_all(compositor))


def is_element(element):
    return isinstance(element, elements.Element)


def is_particle(xsdtype):
    return isinstance(xsdtype, uses.Particle)


def is_sequence(sequence):
    return isinstance(sequence, elements.Sequence)


def is_schema(schema):
    return isinstance(schema, elements.Schema)


def is_xmlattribute(xsdtype):
    return isinstance(xsdtype, base.XmlAttribute)
