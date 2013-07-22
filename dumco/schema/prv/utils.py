# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.checks


def _particle_index(particle, parent):
    if not dumco.schema.checks.is_particle(particle):
        return None

    particles = (parent.particles
                 if dumco.schema.checks.is_compositor(parent)
                 else [parent.term])

    compositors = {'all': 0, 'chc': 0, 'seq': 0}
    for p in particles:
        if dumco.schema.checks.is_all(p.element):
            if p == particle and compositors['all'] > 0:
                return compositors['all']
            compositors['all'] = compositors['all'] + 1
        elif dumco.schema.checks.is_choice(p.element):
            if p == particle and compositors['chc'] > 0:
                return compositors['chc']
            compositors['chc'] = compositors['chc'] + 1
        elif dumco.schema.checks.is_sequence(p.element):
            if p == particle and compositors['seq'] > 0:
                return compositors['seq']
            compositors['seq'] = compositors['seq'] + 1

    return None


def forge_name(element, parents, factory, names):
    if element.name is not None:
        return

    parent = parents[-1]

    assert (len(parents) > 0 and
            not dumco.schema.checks.is_schema(parent)), \
        'Schema never has a name and generally should not be reached'

    if hasattr(parent, 'name'):
        if parent.name is None:
            forge_name(parent, parents[:-1], factory, names)

        real_elem = element
        if dumco.schema.checks.is_particle(element):
            real_elem = element.element
        real_parent = parent
        if dumco.schema.checks.is_particle(parent):
            real_parent = parent.element

        element.name = factory.namer.name(real_elem, parent.name,
            real_parent.__class__, _particle_index(element, real_parent))

        # Validate naming.
        prefix = ''
        if real_elem.schema is not None:
            prefix = '{{{0}}}:'.format(real_elem.schema.target_ns)
        name = '{0}{1}'.format(prefix, element.name)
        assert name not in names, \
            'Name {0} was already encountered'.format(name)
        names.add(name)
    else:
        forge_name(element, parents[:-1], factory, names)
