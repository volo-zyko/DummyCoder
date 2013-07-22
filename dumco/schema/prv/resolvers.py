# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.base
import dumco.schema.checks


def _parse_qname(qname, namespaces, default=''):
    splitted = qname.split(':')
    if len(splitted) == 1:
        return (None, qname)
    else:
        return (namespaces[splitted[0]], splitted[1])


def resolve_attribute(qname, schema, factory):
    (uri, localname) = _parse_qname(qname, schema.namespaces)
    if uri is None or uri == schema.target_ns:
        return schema.attributes[localname]
    else:
        try:
            return schema.imports[uri].attributes[localname]
        except KeyError:
            return factory.xml_attributes[localname]


def resolve_attribute_group(qname, schema):
    (uri, localname) = _parse_qname(qname, schema.namespaces)
    if uri is None or uri == schema.target_ns:
        return schema.attribute_groups[localname]
    else:
        return schema.imports[uri].attribute_groups[localname]


def resolve_complex_type(qname, schema):
    (uri, localname) = _parse_qname(qname, schema.namespaces)
    if uri is None or uri == schema.target_ns:
        return schema.complex_types[localname]
    else:
        return schema.imports[uri].complex_types[localname]


def resolve_element(qname, schema):
    (uri, localname) = _parse_qname(qname, schema.namespaces)
    if uri is None or uri == schema.target_ns:
        return schema.elements[localname]
    else:
        return schema.imports[uri].elements[localname]


def resolve_group(qname, schema):
    (uri, localname) = _parse_qname(qname, schema.namespaces)
    if uri is None or uri == schema.target_ns:
        return schema.groups[localname]
    else:
        return schema.imports[uri].groups[localname]


def resolve_simple_type(qname, schema, factory):
    (uri, localname) = _parse_qname(qname, schema.namespaces)
    if uri is None or uri == schema.target_ns:
        return schema.simple_types[localname]
    else:
        if dumco.schema.checks.is_xsd_namespace(uri):
            return factory.simple_types[localname]

        return schema.imports[uri].simple_types[localname]


def resolve_type(qname, schema, factory):
    try:
        return resolve_simple_type(qname, schema, factory)
    except KeyError:
        return resolve_complex_type(qname, schema)
