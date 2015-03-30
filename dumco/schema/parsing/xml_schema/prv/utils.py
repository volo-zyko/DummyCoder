# Distributed under the GPLv2 License; see accompanying file COPYING.

import copy
import operator

from dumco.schema.dumping.write_xml import TagGuard, XmlWriter
from dumco.schema.xsd_types import XSD_NAMESPACE
from dumco.schema.rng_types import RNG_NAMESPACE

import dumco.schema.checks
import dumco.schema.model as model


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


def parse_any_namespace(namespace, schema):
    constraints = []
    if namespace == '##any':
        pass
    elif namespace == '##other':
        if schema.dom_element.target_ns is not None:
            constraints = [
                model.Any.Not(model.Any.Name(schema.dom_element.target_ns,
                                             None))]
    else:
        def fold_namespaces(accum, u):
            if u == '##targetNamespace':
                if schema.dom_element.target_ns is None:
                    return accum

                return accum + [
                    model.Any.Name(schema.dom_element.target_ns, None)]
            elif u == '##local':
                return accum
            return accum + [model.Any.Name(u, None)]

        constraints = reduce(fold_namespaces, namespace.split(), [])

    if len(constraints) == 0:
        anys = [model.Any(
                None, schema.dom_element)]
    elif len(constraints) == 1:
        anys = [model.Any(
                constraints[0], schema.dom_element)]
    else:
        anys = [model.Any(c, schema.dom_element)
                for c in constraints]

    return anys


def eliminate_degenerate_simple_type(st):
    if (dumco.schema.checks.is_restriction_type(st) and
            not st.restriction.enumerations and
            st.restriction.fraction_digits is None and
            st.restriction.length is None and
            st.restriction.max_exclusive is None and
            st.restriction.max_inclusive is None and
            st.restriction.max_length is None and
            st.restriction.min_exclusive is None and
            st.restriction.min_inclusive is None and
            st.restriction.min_length is None and
            not st.restriction.patterns and
            st.restriction.total_digits is None and
            st.restriction.white_space is None):
        return st.restriction.base

    return st


def connect_restriction_base(restriction, base):
    if dumco.schema.checks.is_list_type(base):
        _simplify_list_restiction(base, restriction.length,
                                  restriction.min_length,
                                  restriction.max_length)
        return base

    restriction.base = _merge_base_restriction(restriction, base)

    return restriction


def _merge_base_restriction(restriction, base):
    def merge(attr):
        if not getattr(restriction, attr):
            value = getattr(base.restriction, attr)
            if not value:
                setattr(restriction, attr, value)

    if dumco.schema.checks.is_restriction_type(base):
        merge('enumerations')
        merge('fraction_digits')
        merge('length')
        merge('max_exclusive')
        merge('max_inclusive')
        merge('max_length')
        merge('min_exclusive')
        merge('min_inclusive')
        merge('min_length')
        merge('patterns')
        merge('total_digits')
        merge('white_space')

        base = _merge_base_restriction(restriction, base.restriction.base)

    return base


def _simplify_list_restiction(base, length, min_length, max_length):
    assert dumco.schema.checks.is_list_type(base)

    itemtype = base.listitems[0]

    min_occurs = itemtype.min_occurs
    max_occurs = itemtype.max_occurs

    if length is not None:
        min_occurs = length
        max_occurs = length

    if min_length is not None:
        min_occurs = min_length

    if max_length is not None:
        max_occurs = max_length

    base.listitems[0] = dumco.schema.uses.ListTypeCardinality(
        itemtype[0], min_occurs, max_occurs)


def dump_value_constraint(constraint, context):
    if constraint.fixed:
        assert constraint.value, \
            'Constraint has fixed value but the value itself is unknown'
        context.add_attribute('fixed', constraint.value)
    elif constraint.value is not None:
        context.add_attribute('default', constraint.value)


class XsdDumpContext(XmlWriter):
    def __init__(self, out, schema):
        super(XsdDumpContext, self).__init__(out)

        # Mapping prefix:uri.
        self.xsd_imports = {}
        self.schema = schema

    def set_current_schema(self, current_schema):
        self.schema = current_schema

    def qname(self, component):
        assert component.schema is not None and self.schema is not None

        if component.dom_element != self.schema:
            assert (component.dom_element.prefix not in self.xsd_imports or
                    self.xsd_imports[component.dom_element.prefix] ==
                    component.dom_element.target_ns)

            self.xsd_imports[component.dom_element.prefix] = \
                component.dom_element.target_ns

            return '{}:{}'.format(component.schema.prefix, component.name)

        return component.name

    def type_qname(self, component):
        if component.dom_element.target_ns == RNG_NAMESPACE:
            return 'xsd:{}'.format(component.name)

        return self.qname(component)


class XsdTagGuard(TagGuard):
    def __init__(self, tag, writer):
        super(self, TagGuard).__init__(writer, tag, XSD_NAMESPACE)
