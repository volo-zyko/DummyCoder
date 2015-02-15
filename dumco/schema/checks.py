# Distributed under the GPLv2 License; see accompanying file COPYING.

import base
import model
import uses
import xsd_types


def _attribute_count(schema_type):
    if is_complex_type(schema_type):
        return len(list(schema_type.attribute_uses()))
    return 0


# General checks.
def is_xsd_namespace(uri):
    return (uri == xsd_types.XSD_NAMESPACE or
            uri == xsd_types.XSD_DATATYPES_NAMESPACE)


def is_xml_namespace(uri):
    return uri == base.XML_NAMESPACE


# Type checks.
def has_complex_content(schema_type):
    # If CT has any particle then it has complex content.
    if not is_complex_type(schema_type):
        return False

    for _ in schema_type.particles():
        return True
    else:
        return False


def has_supported_complex_content(schema_type, om):
    # If CT has any particle then it has complex content.
    if not is_complex_type(schema_type):
        return False

    return any([not om.is_opaque_ct_member(schema_type, p.term)
                for p in schema_type.particles()])


def has_empty_content(schema_type):
    # If CT has neither particles nor text then it has empty content.
    # Note: Attributes are not checked.
    if not is_complex_type(schema_type):
        return False

    for _ in schema_type.particles():
        return False
    else:
        return schema_type.text() is None


def has_simple_content(schema_type):
    # If CT has only text content then it has simple content.
    # Note: Attributes are not checked.
    if not is_complex_type(schema_type):
        return False

    for _ in schema_type.particles():
        return False
    else:
        return schema_type.text() is not None


def has_supported_simple_content(schema_type, om):
    # If CT has only text content then it has simple content.
    # Note: Attributes are not checked.
    if not is_complex_type(schema_type):
        return False

    if any([not om.is_opaque_ct_member(schema_type, p.term)
            for p in schema_type.particles()]):
        return False
    else:
        return (schema_type.text() is not None and
                not om.is_opaque_ct_member(schema_type, schema_type.text()))


def is_complex_type(schema_type):
    return isinstance(schema_type, model.ComplexType)


def is_complex_urtype(schema_type):
    return (is_complex_type(schema_type) and
            is_xsd_namespace(schema_type.schema.target_ns) and
            schema_type.name == 'anyType')


def is_empty_complex_type(schema_type):
    return (has_empty_content(schema_type) and
            _attribute_count(schema_type) == 0)


def is_enumeration_type(schema_type):
    return (is_restriction_type(schema_type) and
            len(schema_type.restriction.enumerations) > 0)


def is_list_type(schema_type):
    return (is_simple_type(schema_type) and schema_type.listitems)


def is_native_type(schema_type):
    return isinstance(schema_type, base.NativeType)


def is_primitive_type(schema_type):
    return (is_native_type(schema_type) or is_simple_type(schema_type))


def is_restriction_type(schema_type):
    return (is_simple_type(schema_type) and
            schema_type.restriction is not None)


def is_simple_type(schema_type):
    return isinstance(schema_type, model.SimpleType)


def is_simple_urtype(schema_type):
    return (is_simple_type(schema_type) and
            is_xsd_namespace(schema_type.schema.target_ns) and
            schema_type.name == 'anySimpleType')


def is_single_attribute_type(schema_type):
    return (has_empty_content(schema_type) and
            _attribute_count(schema_type) == 1)


def is_single_valued_type(schema_type):
    # A type with either single attribute or with text content only or
    # empty complex type or simple type.
    return (is_primitive_type(schema_type) or
            is_empty_complex_type(schema_type) or
            is_text_complex_type(schema_type) or
            is_single_attribute_type(schema_type))


def is_text_complex_type(schema_type):
    return (has_simple_content(schema_type) and
            _attribute_count(schema_type) == 0)


def is_union_type(schema_type):
    return (is_simple_type(schema_type) and schema_type.union)


def is_xsd_native_type(schema_type):
    return (isinstance(schema_type, base.NativeType) and
            is_xsd_namespace(schema_type.uri))


# Element checks.
def is_any(schema_any):
    return isinstance(schema_any, model.Any)


def is_attribute(attr):
    return isinstance(attr, model.Attribute)


def is_attribute_use(attr):
    return isinstance(attr, uses.AttributeUse)


def is_choice(choice):
    return isinstance(choice, model.Choice)


def is_compositor(compositor):
    return isinstance(compositor, base.Compositor)


def is_element(element):
    return isinstance(element, model.Element)


def is_interleave(interleave):
    return isinstance(interleave, model.Interleave)


def is_particle(particle):
    return isinstance(particle, uses.Particle)


def is_restriction(restriction):
    return isinstance(restriction, model.Restriction)


def is_sequence(sequence):
    return isinstance(sequence, model.Sequence)


def is_schema(schema):
    return isinstance(schema, model.Schema)


def is_terminal(term):
    return is_element(term) or is_any(term)


def is_text(text):
    return isinstance(text, uses.SchemaText)


def is_xml_attribute(attr):
    return (is_attribute(attr) and
            is_xml_namespace(attr.schema.target_ns))
