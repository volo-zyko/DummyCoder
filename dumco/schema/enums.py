# Distributed under the GPLv2 License; see accompanying file COPYING.

import checks


def enum_flat(ct):
    for u in ct.attribute_uses():
        yield u

    if ct.text() is not None:
        yield ct.text()

    for p in ct.particles():
        yield p


def enum_hierarchy(ct):
    for u in ct.attribute_uses(flatten=False):
        yield u

    if ct.text() is not None:
        yield ct.text(flatten=False)

    for p in ct.particles(flatten=False):
        yield p


def enum_supported_attributes_flat(ct, om):
    for u in ct.attribute_uses():
        if not om.is_opaque_ct_member(ct, u.attribute, True):
            yield u


def enum_supported_elements_flat(ct, om):
    for p in ct.particles():
        if not om.is_opaque_ct_member(ct, p.term):
            yield p


def enum_supported_flat(ct, om):
    for u in enum_supported_attributes_flat(ct, om):
        yield u

    if ct.text() is not None:
        if not om.is_opaque_ct_member(ct, ct.text()):
            yield ct.text()

    for p in enum_supported_elements_flat(ct, om):
        yield p


def enum_supported_attributes_hierarchy(ct, om):
    for u in ct.attribute_uses(flatten=False):
        if not om.is_opaque_ct_member(ct, u[1].attribute, True):
            yield u


def enum_supported_elements_hierarchy(ct, om):
    for p in ct.particles(flatten=False):
        if not om.is_opaque_ct_member(ct, p[1].term):
            yield p


def enum_supported_hierarchy(ct, om):
    for u in enum_supported_attributes_hierarchy(ct, om):
        yield u

    if ct.text() is not None:
        if not om.is_opaque_ct_member(ct, ct.text()):
            yield ct.text(flatten=False)

    for p in enum_supported_elements_hierarchy(ct, om):
        yield p


def get_supported_single_attribute(ct, om):
    assert checks.is_supported_single_attribute_type(ct, om)

    for u in enum_supported_attributes_flat(ct, om):
        return u
