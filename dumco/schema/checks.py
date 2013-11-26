# Distributed under the GPLv2 License; see accompanying file COPYING.

import base
import elements
import enums
import uses
import xsd_types


def _attribute_count(schema_type):
    if is_complex_type(schema_type):
        return len(list(enums.enum_attribute_uses(schema_type)))
    return 0


# General checks.
def is_xsd_namespace(uri):
    return (uri == xsd_types.XSD_NAMESPACE or
            uri == xsd_types.XSD_DATATYPES_NAMESPACE)


def is_xml_namespace(uri):
    return uri == base.XML_NAMESPACE


# Type checks.
def has_complex_content(schema_type):
    return (is_complex_type(schema_type) and
            schema_type.particle is not None and schema_type.text is None)


def has_empty_content(schema_type):
    return (is_complex_type(schema_type) and
            schema_type.particle is None and schema_type.text is None)


def has_simple_content(schema_type):
    return (is_complex_type(schema_type) and
            schema_type.particle is None and schema_type.text is not None)


def is_attributed_complex_type(schema_type):
    return (has_empty_content(schema_type) and
            _attribute_count(schema_type) == 1)


def is_complex_type(schema_type):
    return isinstance(schema_type, elements.ComplexType)


def is_complex_urtype(schema_type):
    return (is_complex_type(schema_type) and schema_type.schema is None and
            schema_type.name == 'anyType')


def is_empty_complex_type(schema_type):
    return (has_empty_content(schema_type) and
            _attribute_count(schema_type) == 0)


def is_list_type(schema_type):
    return (is_simple_type(schema_type) and schema_type.listitem is not None)


def is_native_type(schema_type):
    return isinstance(schema_type, base.NativeType)


def is_primitive_type(schema_type):
    return (is_native_type(schema_type) or is_simple_type(schema_type))


def is_restriction_type(schema_type):
    return (is_simple_type(schema_type) and schema_type.restriction is not None)


def is_simple_type(schema_type):
    return isinstance(schema_type, elements.SimpleType)


def is_simple_urtype(schema_type):
    return (is_simple_type(schema_type) and schema_type.schema is None and
            schema_type.name == 'anySimpleType')


def is_text_complex_type(schema_type):
    return (has_simple_content(schema_type) and
            _attribute_count(schema_type) == 0)


def is_union_type(schema_type):
    return (is_simple_type(schema_type) and schema_type.union)


def is_xsd_native_type(schema_type):
    return (isinstance(schema_type, base.NativeType) and
            is_xsd_namespace(schema_type.uri))


# Element checks.
def is_all(schema_all):
    return isinstance(schema_all, elements.All)


def is_any(schema_any):
    return isinstance(schema_any, elements.Any)


def is_attribute(attr):
    return isinstance(attr, elements.Attribute)


def is_attribute_use(attr):
    return isinstance(attr, uses.AttributeUse)


def is_base(schema):
    return isinstance(schema, base.SchemaBase)


def is_choice(choice):
    return isinstance(choice, elements.Choice)


def is_compositor(compositor):
    return (is_sequence(compositor) or is_choice(compositor) or
            is_all(compositor))


def is_element(element):
    return isinstance(element, elements.Element)


def is_particle(particle):
    return isinstance(particle, uses.Particle)


def is_sequence(sequence):
    return isinstance(sequence, elements.Sequence)


def is_schema(schema):
    return isinstance(schema, elements.Schema)


def is_text(text):
    return isinstance(text, base.SchemaText)


def is_xml_attribute(attr):
    return (isinstance(attr, base.XmlAttribute) or
            (is_attribute(attr) and is_xml_namespace(attr.schema.target_ns)))
