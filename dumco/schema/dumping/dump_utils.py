# Distributed under the GPLv2 License; see accompanying file COPYING.

import operator

import dumco.schema.base as base
import dumco.schema.checks as checks
import dumco.schema.enums as enums
import dumco.schema.model as model
import dumco.schema.rng_types as rng_types
import dumco.schema.tuples as tuples
import dumco.schema.uses as uses
from dumco.utils.horn import horn


def _type_qname(name, own_schema, other_schema, context):
    if own_schema.target_ns == rng_types.RNG_NAMESPACE:
        return 'xsd:{}'.format(name)
    return _qname(name, own_schema, other_schema, context)


def _element_form(elem, context):
    elem_form = context.element_forms.get(elem.schema, None)
    if elem_form is not None:
        if ((not elem.qualified and not elem_form) or
                (elem.qualified and elem_form)):
            return None
        elif elem.qualified:
            return 'qualified'
        else:
            return 'unqualified'
    else:
        return None


def _attribute_form(attr, context):
    attr_form = context.attribute_forms.get(attr.schema, None)
    if attr_form is not None:
        if ((not attr.qualified and not attr_form) or
                (attr.qualified and attr_form)):
            return None
        elif attr.qualified:
            return 'qualified'
        else:
            return 'unqualified'
    else:
        return None


def is_top_level_attribute(attr_use):
    # Required and default value should not be present at the same time.
    assert (not attr_use.required or attr_use.constraint.fixed or
            attr_use.constraint.value is None)
    return (attr_use.required and not attr_use.attribute.constraint.fixed and
            attr_use.attribute.constraint.value is not None)


def dump_restriction(restriction, schema, context):
    with TagGuard('restriction', context):
        context.add_attribute(
            'base', _type_qname(restriction.base.name, restriction.base.schema,
                                schema, context))

        if restriction.enumerations:
            for e in restriction.enumerations:
                with TagGuard('enumeration', context):
                    context.add_attribute('value', e.value)
        if restriction.fraction_digits is not None:
            with TagGuard('fractionDigits', context):
                context.add_attribute('value', restriction.fraction_digits)
        if restriction.length is not None:
            with TagGuard('length', context):
                context.add_attribute('value', restriction.length)
        if restriction.max_exclusive is not None:
            with TagGuard('maxExclusive', context):
                context.add_attribute('value', restriction.max_exclusive)
        if restriction.max_inclusive is not None:
            with TagGuard('maxInclusive', context):
                context.add_attribute('value', restriction.max_inclusive)
        if restriction.max_length is not None:
            with TagGuard('maxLength', context):
                context.add_attribute('value', restriction.max_length)
        if restriction.min_exclusive is not None:
            with TagGuard('minExclusive', context):
                context.add_attribute('value', restriction.min_exclusive)
        if restriction.min_inclusive is not None:
            with TagGuard('minInclusive', context):
                context.add_attribute('value', restriction.min_inclusive)
        if restriction.min_length is not None:
            with TagGuard('minLength', context):
                context.add_attribute('value', restriction.min_length)
        if restriction.patterns:
            for p in restriction.patterns:
                with TagGuard('pattern', context):
                    context.add_attribute('value', p)
        if restriction.total_digits is not None:
            with TagGuard('totalDigits', context):
                context.add_attribute('value', restriction.total_digits)
        if restriction.white_space is not None:
            if restriction.white_space == model.Restriction.WS_PRESERVE:
                value = 'preserve'
            elif restriction.white_space == model.Restriction.WS_REPLACE:
                value = 'replace'
            elif restriction.white_space == model.Restriction.WS_COLLAPSE:
                value = 'collapse'
            with TagGuard('whiteSpace', context):
                context.add_attribute('value', value)


def dump_listitems(listitems, schema, context):
    assert len(listitems) == 1, 'Cannot dump xsd:list'

    with TagGuard('list', context):
        context.add_attribute(
            'itemType', _type_qname(listitems[0].type.name,
                                    listitems[0].type.schema,
                                    schema, context))


def dump_union(union, schema, context):
    assert all([checks.is_primitive_type(m) for m in union])

    with TagGuard('union', context):
        context.add_attribute(
            'memberTypes',
            ' '.join([_type_qname(m.name, m.schema, schema, context)
                      for m in union]))


def dump_simple_content(ct, schema, context):
    with TagGuard('simpleContent', context):
        with TagGuard('extension', context):
            qn = _type_qname(ct.text().type.name, ct.text().type.schema,
                             schema, context)
            context.add_attribute('base', qn)

            dump_attribute_uses(ct, schema, context)


def _dump_occurs_attributes(min_occurs, max_occurs, context):
    if min_occurs != 1:
        context.add_attribute('minOccurs', min_occurs)
    if max_occurs != 1:
        context.add_attribute('maxOccurs', 'unbounded'
                              if max_occurs == base.UNBOUNDED
                              else max_occurs)


def dump_particle(ct, schema, context):
    def dump_element(particle, min_occurs, max_occurs):
        groups = context.egroups.get(particle.term.schema, {})

        hashable_particle = tuples.HashableParticle(particle, None)
        if hashable_particle in groups.iterkeys():
            group_name = groups[hashable_particle].name

            with TagGuard('group', context):
                context.add_attribute(
                    'ref', _qname(group_name, particle.term.schema,
                                  schema, context))

            return

        top_elements = particle.term.schema.elements
        is_element_definition = particle.term not in top_elements

        with TagGuard('element', context):
            _dump_occurs_attributes(min_occurs, max_occurs, context)

            dump_element_attributes(particle.term, is_element_definition,
                                    schema, context)

            form = (None if not is_element_definition
                    else _element_form(particle.term, context))
            if form is not None:
                context.add_attribute('form', form)

    def dump_any(particle, min_occurs, max_occurs):
        constraint = _get_any_constraint_text(particle.term.constraint, schema)

        with TagGuard('any', context):
            _dump_occurs_attributes(min_occurs, max_occurs, context)

            context.add_attribute('namespace', constraint)

    def dump_terminal(level, subparents, subpart):
        if level < len(subparents):
            min_occurs = reduce(
                lambda acc, x: uses.min_occurs_op(acc, x.min_occurs,
                                                  operator.mul),
                subparents[level:], 1)
            max_occurs = reduce(
                lambda acc, x: uses.max_occurs_op(acc, x.max_occurs,
                                                  operator.mul),
                subparents[level:], 1)

            min_occurs = uses.min_occurs_op(min_occurs, subpart.min_occurs,
                                            operator.mul)
            max_occurs = uses.max_occurs_op(max_occurs, subpart.max_occurs,
                                            operator.mul)
        else:
            min_occurs = subpart.min_occurs
            max_occurs = subpart.max_occurs

        if checks.is_element(subpart.term):
            dump_element(subpart, min_occurs, max_occurs)
        elif checks.is_any(subpart.term):
            dump_any(subpart, min_occurs, max_occurs)

    def dump_compositor(comp_name, comp_min, comp_max, hierarchy, level):
        with TagGuard(comp_name, context):
            _dump_occurs_attributes(comp_min, comp_max, context)

            dump_hierarchy(hierarchy, level, False)

    def get_compositor_info(particle, is_first_in_ct):
        if checks.is_interleave(particle.term):
            members = [m for m in particle.term.members
                       if (checks.is_particle(m) and
                           not context.om.is_opaque_ct_member(ct, m.term))]

            if (particle.max_occurs == 1 and
                    all([(checks.is_element(m.term) and
                          m.max_occurs <= 1) for m in members]) and
                    is_first_in_ct):
                return (particle.min_occurs,
                        particle.max_occurs, 'all')
            else:
                horn.peep('Cannot represent xsd:all. Approximating '
                          'with xsd:choice')
                return (0, base.UNBOUNDED, 'choice')

        return (particle.min_occurs, particle.max_occurs,
                particle.term.__class__.__name__.lower())

    def dump_hierarchy(hierarchy, level, is_first_compositor):
        assert hierarchy

        subhierarchies = [[]]

        curr_parents = hierarchy[0][0]
        for (parents, part) in hierarchy:
            if (level < len(curr_parents) and level < len(parents) and
                    curr_parents[level] == parents[level]):
                subhierarchies[-1].append((parents, part))
                continue

            curr_parents = parents
            if subhierarchies[-1]:
                subhierarchies.append([(parents, part)])
            else:
                subhierarchies[-1].append((parents, part))

        for subhierarchy in subhierarchies:
            len_subhierarchy = len(subhierarchy)

            if (len_subhierarchy > 1 or
                    (len_subhierarchy == 1 and level == 0)):
                (subparents, subpart) = subhierarchy[0]

                if len_subhierarchy == 1:
                    # Handle the case when we have to dump compositor with
                    # single child and this compositor is the first child of
                    # complex type. We always convert it to sequence because
                    # on loading we load such cases only as sequence.
                    with TagGuard('sequence', context):
                        dump_terminal(level, subparents, subpart)

                    continue

                (comp_min, comp_max, comp_name) = \
                    get_compositor_info(subparents[level], is_first_compositor)

                sublevel = level + 1
                while sublevel < len(subparents):
                    subparent = subparents[sublevel]
                    if all([sublevel < len(ps) and subparent == ps[sublevel]
                            for (ps, p) in subhierarchy]):
                        sublevel = sublevel + 1

                        (c_min, c_max, comp_name) = \
                            get_compositor_info(subparent, is_first_compositor)

                        comp_min = uses.min_occurs_op(comp_min, c_min,
                                                      operator.mul)
                        comp_max = uses.max_occurs_op(comp_max, c_max,
                                                      operator.mul)
                    else:
                        break

                dump_compositor(comp_name, comp_min, comp_max,
                                subhierarchy, sublevel)
            elif len_subhierarchy == 1:
                (subparents, subpart) = subhierarchy[0]

                dump_terminal(level, subparents, subpart)

    root = [(p[1:], x) for (p, x)
            in enums.enum_supported_elements_hierarchy(ct, context.om)]

    dump_hierarchy(root, 0, True)


def dump_attribute_uses(ct, schema, context):
    def enum_sorted_attributes(ct, schema):
        if checks.is_single_attribute_type(ct):
            yield enums.get_single_attribute(ct)
            return

        for u in sorted(enums.enum_supported_attributes_flat(ct, context.om),
                        key=lambda u: uses.attribute_key(u, schema)):
            yield u

    anys = []
    for u in enum_sorted_attributes(ct, schema):
        if checks.is_attribute(u.attribute):
            dump_attribute_use(u, schema, context)
        elif checks.is_any(u.attribute):
            anys.append(u.attribute)

    if anys:
        constraints = [_get_any_constraint_text(a.constraint, schema)
                       for a in anys]

        with TagGuard('anyAttribute', context):
            if any([c == '##any' for c in constraints]):
                context.add_attribute('namespace', '##any')
            elif any([c == '##other' for c in constraints]):
                if any([c == schema.target_ns for c in constraints]):
                    context.add_attribute('namespace', '##any')
                else:
                    context.add_attribute('namespace', '##other')
            else:
                context.add_attribute('namespace', ' '.join(constraints))


def dump_element_particle(particle, schema, context):
    assert checks.is_element(particle.term)

    with TagGuard('element', context):
        _dump_occurs_attributes(
            particle.min_occurs, particle.max_occurs, context)

        dump_element_attributes(particle.term, True, schema, context)

        form = _element_form(particle.term, context)
        if form is not None:
            context.add_attribute('form', form)


def dump_attribute_use(attr_use, schema, context):
    assert checks.is_attribute(attr_use.attribute)

    attribute = attr_use.attribute

    if (not checks.is_xml_attribute(attribute) and
            not is_top_level_attribute(attr_use) and
            attribute.schema != schema):
        # We reference attribute from other schema but since in most cases
        # we don't want to maintain top-level attributes we can reference then
        # only attribute group.
        groups = context.agroups[attribute.schema]
        group_name = groups[tuples.HashableAttributeUse(attr_use, None)].name
        with TagGuard('attributeGroup', context):
            context.add_attribute(
                'ref',
                _qname(group_name, attribute.schema, schema, context))

        return

    with TagGuard('attribute', context):
        if (checks.is_xml_attribute(attribute) or
                is_top_level_attribute(attr_use)):
            context.add_attribute(
                'ref', _qname(attribute.name, attribute.schema,
                              schema, context))

            _dump_value_constraint(attr_use.constraint, context)
        else:
            dump_attribute_attributes(attribute, schema, context)

            if attribute.constraint.value is None:
                _dump_value_constraint(attr_use.constraint, context)

            form = _attribute_form(attr_use.attribute, context)
            if form is not None:
                context.add_attribute('form', form)

        if attr_use.required:
            context.add_attribute('use', 'required')


def dump_attribute_attributes(attribute, schema, context):
    assert checks.is_attribute(attribute)

    context.add_attribute(
        'name',
        _qname(attribute.name, attribute.schema, schema, context))

    if not checks.is_simple_urtype(attribute.type):
        context.add_attribute(
            'type', _type_qname(attribute.type.name, attribute.type.schema,
                                schema, context))

    _dump_value_constraint(attribute.constraint, context)


def dump_element_attributes(element, is_element_definition,
                            schema, context):
    assert checks.is_element(element)

    if is_element_definition:
        context.add_attribute(
            'name',
            _qname(element.name, element.schema, schema, context))

        if (not checks.is_complex_urtype(element.type) and
                not checks.is_simple_urtype(element.type)):
            context.add_attribute(
                'type', _type_qname(element.type.name, element.type.schema,
                                    schema, context))

        _dump_value_constraint(element.constraint, context)
    else:
        context.add_attribute(
            'ref',
            _qname(element.name, element.schema, schema, context))


def _dump_value_constraint(constraint, context):
    if constraint.fixed:
        assert constraint.value, \
            'Constraint has fixed value but the value itself is unknown'
        context.add_attribute('fixed',
                              constraint.value)
    elif constraint.value is not None:
        context.add_attribute('default',
                              constraint.value)


def _get_any_constraint_text(constraint, schema):
    if constraint is None:
        return '##any'
    elif (isinstance(constraint, model.Any.Not) and
          constraint.name.ns == schema.target_ns and
          constraint.name.tag is None):
        return '##other'
    elif (isinstance(constraint, model.Any.Name) and
          constraint.ns == schema.target_ns and constraint.tag is None):
        return '##targetNamespace'
    elif (isinstance(constraint, model.Any.Name) and
          constraint.ns is not None and constraint.tag is None):
        return constraint.ns
    else:
        horn.peep(
            'Cannot represent constraint \'{}\' for xsd:any. '
            'Approximating with ##any'.format(str(constraint)))
        return '##any'
