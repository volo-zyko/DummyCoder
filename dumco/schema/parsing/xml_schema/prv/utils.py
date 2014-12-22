# Distributed under the GPLv2 License; see accompanying file COPYING.

import copy
import operator

import dumco.schema.checks


def restrict_base_attributes(base, factory, prohibited, redefined):
    # Utility function common for XsdSimpleRestriction and
    # XsdComplexRestriction which add attribute uses only if they are not
    # restricted by derived type.
    def is_attr_in_list(attr, attrlist):
        return any([attr.name == x.attribute.name for x in attrlist])

    res_attr_uses = []
    for u in base.attribute_uses():
        if (not dumco.schema.checks.is_any(u.attribute) and
                (is_attr_in_list(u.attribute, prohibited) or
                 is_attr_in_list(u.attribute, redefined))):
            continue

        res_attr_uses.append(u)

    return res_attr_uses


def reduce_particle(particle):
    if particle is None or not dumco.schema.checks.is_compositor(particle.term):
        return particle

    particle.term.members = [m for m in particle.term.members if m is not None]

    if len(particle.term.members) == 1:
        m = copy.copy(particle.term.members[0])
        m.min_occurs = \
            dumco.schema.uses.min_occurs_op(particle.min_occurs,
                                            m.min_occurs, operator.mul)
        m.max_occurs = \
            dumco.schema.uses.max_occurs_op(particle.max_occurs,
                                            m.max_occurs, operator.mul)
        return m
    elif not particle.term.members:
        return None

    return particle
