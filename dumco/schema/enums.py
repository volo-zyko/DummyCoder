# Distributed under the GPLv2 License; see accompanying file COPYING.

import checks


def enum_attribute_uses(ct):
    for a in ct.attributes:
        yield ([ct], a)


def enum_ct_particles(ct):
    if ct.particle is None:
        return

    for p in _enum_particles_with_parents([ct], ct.particle.term):
        yield p


def enum_plain_content(ct):
    for a in enum_attribute_uses(ct):
        yield a

    for p in enum_ct_particles(ct):
        yield p

    if ct.mixed:
        yield ([ct], ct.text)


def enum_term_particles(term):
    if term is None:
        return

    for p in _enum_particles_with_parents([term], term):
        yield p


def _enum_particles_with_parents(parents, term):
    for p in term.particles:
        assert (checks.is_particle(p) and
                (checks.is_element(p.term) or checks.is_any(p.term) or
                checks.is_compositor(p.term))), \
            'Unknown particle'

        if checks.is_element(p.term) or checks.is_any(p.term):
            yield (parents, p)
        elif checks.is_compositor(p.term):
            for e in _enum_particles_with_parents(parents + [p.term], p.term):
                yield e
