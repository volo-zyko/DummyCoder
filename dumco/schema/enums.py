# Distributed under the GPLv2 License; see accompanying file COPYING.


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


def enum_supported_flat(ct, om):
    for u in ct.attribute_uses():
        if not om.is_opaque_ct_member(ct, u.attribute):
            yield u

    if ct.text() is not None:
        if not om.is_opaque_ct_member(ct, ct.text()):
            yield ct.text()

    for p in ct.particles():
        if not om.is_opaque_ct_member(ct, p.term):
            yield p
