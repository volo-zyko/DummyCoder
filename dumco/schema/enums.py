# Distributed under the GPLv2 License; see accompanying file COPYING.

import checks


def enum_attribute_uses(ct):
    for a in ct.attributes:
        yield ([ct], a)


def enum_plain_content(ct):
    for a in enum_attribute_uses(ct):
        yield a

    for p in enum_particles(ct):
        yield p

    if ct.mixed:
        yield ([ct], ct.text)


def enum_particles(ct):
    if ct.particle is None:
        return

    def enum_particles_with_parents(parents, particle):
        for p in particle.term.particles:
            assert (checks.is_particle(p) and
                    (checks.is_element(p.term) or checks.is_any(p.term) or
                    checks.is_compositor(p.term))), \
                'Unknown particle'

            if checks.is_element(p.term) or checks.is_any(p.term):
                yield (parents, p)
            elif checks.is_compositor(p.term):
                for e in enum_particles_with_parents(parents + [p.term], p):
                    yield e

    for p in enum_particles_with_parents([ct], ct.particle):
        yield p
