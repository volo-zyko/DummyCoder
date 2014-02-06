# Distributed under the GPLv2 License; see accompanying file COPYING.


def enum_plain_content(ct):
    for u in ct.attribute_uses():
        yield u

    for p in ct.particles():
        yield p

    if ct.mixed:
        yield ct.text()
