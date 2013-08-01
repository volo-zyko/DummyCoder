# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.checks


def forge_name(element, parents, namer, forged_names):
    if element.name is not None:
        return

    parent = parents[-1]
    assert (dumco.schema.checks.is_particle(parent) or
            dumco.schema.checks.is_complex_type(parent) or
            dumco.schema.checks.is_simple_type(parent) or
            dumco.schema.checks.is_element(parent) or
            dumco.schema.checks.is_attribute(parent))
    assert len(parents) > 0, 'Not enough parents to forge a name'
    assert parent.name is not None

    element.name = namer.name(element, parent)

    while True:
        try:
            # Validate naming.
            forged_names.add(element)
            break
        except NameForgeException:
            element.name = namer.name(element, parent, with_index=True)


class ValidatingNameSet(set):
    def add(self, elem):
        element = elem
        if dumco.schema.checks.is_particle(elem):
            element = elem.term

        prefix = ''
        if element.schema is not None:
            prefix = '{{{0}}}:'.format(element.schema.target_ns)
        name = '{0}{1}'.format(prefix, elem.name)

        if name in self:
            raise NameForgeException()

        assert name not in self, \
            'Name {0} was already defined'.format(name)

        super(ValidatingNameSet, self).add(name)


class NameForgeException(BaseException):
    pass


class CommonNamer(object):
    def __init__(self):
        self.force_index = 0

    def name(self, element, parent, with_index=False):
        if with_index:
            self.force_index += 1

        parent_name = parent.name

        if dumco.schema.checks.is_complex_type(element):
            if dumco.schema.checks.is_element(parent):
                return self._name_ct_from_parent_elem(
                    parent_name, self.force_index if with_index else '')
            else: # pragma: no cover
                assert False
        elif dumco.schema.checks.is_simple_type(element):
            if dumco.schema.checks.is_element(parent):
                return self._name_st_from_parent_elem(
                    parent_name, self.force_index if with_index else '')
            elif dumco.schema.checks.is_attribute(parent):
                return self._name_st_from_parent_attr(
                    parent_name, self.force_index if with_index else '')
            elif dumco.schema.checks.is_complex_type(parent):
                return self._name_st_from_parent_ct(
                    parent_name, self.force_index if with_index else '')
            elif dumco.schema.checks.is_restriction_type(parent):
                return self._name_st_from_parent_restriction_st(
                    parent_name, self.force_index if with_index else '')
            elif dumco.schema.checks.is_union_type(parent):
                if element in parent.union:
                    tmp = parent.union.index(element)
                else:
                    # SubST was reduced when constructing union ST.
                    tmp = self.force_index

                index = str(tmp) if tmp > 0 else ''
                return self._name_st_from_parent_union_st(
                    parent_name, index, self.force_index if with_index else '')
            elif dumco.schema.checks.is_list_type(parent):
                return self._name_st_from_parent_list_st(
                    parent_name, self.force_index if with_index else '')
            else: # pragma: no cover
                assert False
        elif dumco.schema.checks.is_particle(element):
            assert (dumco.schema.checks.is_particle(parent) or
                    dumco.schema.checks.is_complex_type(parent))

            index = ''
            if dumco.schema.checks.is_particle(parent):
                tmp = self._particle_index(element, parent.term)
                index = str(tmp) if tmp is not None else ''

            if dumco.schema.checks.is_sequence(element.term):
                return self._name_sequence(
                    parent_name, index, self.force_index if with_index else '')
            elif dumco.schema.checks.is_choice(element.term):
                return self._name_choice(
                    parent_name, index, self.force_index if with_index else '')
            elif dumco.schema.checks.is_all(element.term):
                return self._name_all(
                    parent_name, index, self.force_index if with_index else '')
            else: # pragma: no cover
                assert False
        else: # pragma: no cover
            assert False

    @staticmethod
    def _particle_index(particle, parent):
        assert dumco.schema.checks.is_particle(particle)

        particles = (parent.particles
                     if dumco.schema.checks.is_compositor(parent)
                     else [parent.particle])

        compositors = {'all': 0, 'chc': 0, 'seq': 0}
        for p in particles:
            if dumco.schema.checks.is_all(p.term):
                if p == particle and compositors['all'] > 0:
                    return compositors['all']
                compositors['all'] = compositors['all'] + 1
            elif dumco.schema.checks.is_choice(p.term):
                if p == particle and compositors['chc'] > 0:
                    return compositors['chc']
                compositors['chc'] = compositors['chc'] + 1
            elif dumco.schema.checks.is_sequence(p.term):
                if p == particle and compositors['seq'] > 0:
                    return compositors['seq']
                compositors['seq'] = compositors['seq'] + 1

        return None
