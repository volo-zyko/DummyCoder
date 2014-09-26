# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.base as base
import dumco.schema.checks as checks
import dumco.schema.elements as elements
import dumco.schema.xsd_types as xsd_types
import dumco.utils.string_utils


XSD_PREFIX = 'xsd'
XML_PREFIX = 'xml'


class XmlWriter(object):
    def __init__(self):
        self.indentation = 0
        self.namespaces = {}
        self.complex_content = []
        self.is_parent_finalized = True

        self._write('<?xml version="1.0" encoding="UTF-8"?>\n')

    def done(self):
        assert len(self.complex_content) == 0
        self._close()

    def _indent(self):
        self._write(' ' * self.indentation * 2)

    def _finalize_parent_tag(self):
        if not self.is_parent_finalized:
            self._write('>\n')
            self.complex_content[-1:] = [True]
            self.is_parent_finalized = True

    def open_tag(self, prefix, uri, tag):
        self._finalize_parent_tag()
        self.complex_content.append(False)

        self._indent()
        self._write('<{}:{}'.format(prefix, tag))
        self.define_namespace(prefix, uri)
        self.is_parent_finalized = False

        self.indentation += 1

    def add_wellformed_xml(self, xml_string):
        self._finalize_parent_tag()
        self._write(xml_string)

    def close_tag(self, prefix, uri, tag):
        self.indentation -= 1
        if self.complex_content[-1]:
            self._indent()
            self._write('</{}:{}>\n'.format(prefix, tag))
        else:
            self._write('/>\n')
        self.complex_content.pop()
        self.is_parent_finalized = True

    def define_namespace(self, prefix, uri):
        if (prefix in self.namespaces or
                (prefix == XML_PREFIX and uri == base.XML_NAMESPACE)):
            return

        self.namespaces[prefix] = uri
        real_prefix = '' if prefix is None else (':{}'.format(prefix))
        self._write(' xmlns{}="{}"'.format(real_prefix, uri))

    def add_attribute(self, name, value, prefix=''):
        esc_value = dumco.utils.string_utils.quote_xml_attribute(value)
        if prefix != '':
            self._write(' {}:{}={}'.format(prefix, name, esc_value))
        else:
            self._write(' {}={}'.format(name, esc_value))

    def add_comment(self, comment):
        self._finalize_parent_tag()
        self._indent()
        self._write('<!-- {} -->\n'.format(comment))


class TagGuard(object):
    def __init__(self, tag, writer, prefix=XSD_PREFIX,
                 uri=xsd_types.XSD_NAMESPACE):
        self.prefix = prefix
        self.uri = uri
        self.tag = tag
        self.writer = writer

    def __enter__(self):
        self.writer.open_tag(self.prefix, self.uri, self.tag)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.writer.close_tag(self.prefix, self.uri, self.tag)
        return exc_value is None


def _qname(name, own_schema, other_schema, context, prefix=XSD_PREFIX):
    if own_schema != other_schema:
        if own_schema is not None:
            context.store_import_namespace(own_schema.prefix,
                                           own_schema.target_ns)
        elif prefix == XML_PREFIX:
            context.store_import_namespace(None, base.XML_NAMESPACE)
        return '{}:{}'.format(
            own_schema.prefix if own_schema is not None else prefix, name)
    return name


def _max_occurs(value):
    return ('unbounded' if value == base.UNBOUNDED else value)


def _term_name(term):
    if checks.is_interleave(term):
        return 'all'
    return term.__class__.__name__.lower()


def dump_restriction(restriction, schema, context):
    with TagGuard('restriction', context):
        context.add_attribute(
            'base', _qname(restriction.base.name, restriction.base.schema,
                           schema, context))

        if restriction.enumeration:
            for e in restriction.enumeration:
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
        if restriction.pattern is not None:
            with TagGuard('pattern', context):
                context.add_attribute('value', restriction.pattern)
        if restriction.total_digits is not None:
            with TagGuard('totalDigits', context):
                context.add_attribute('value', restriction.total_digits)
        if restriction.white_space is not None:
            if restriction.white_space == elements.Restriction.WS_PRESERVE:
                value = 'preserve'
            elif restriction.white_space == elements.Restriction.WS_REPLACE:
                value = 'replace'
            elif restriction.white_space == elements.Restriction.WS_COLLAPSE:
                value = 'collapse'
            with TagGuard('whiteSpace', context):
                context.add_attribute('value', value)


def dump_listitems(listitems, schema, context):
    assert len(listitems) == 1, 'Cannot dump xs:list'

    with TagGuard('list', context):
        context.add_attribute(
            'itemType', _qname(listitems[0].type.name,
                               listitems[0].type.schema,
                               schema, context))


def dump_union(union, schema, context):
    assert all([checks.is_primitive_type(m) for m in union])

    with TagGuard('union', context):
        context.add_attribute(
            'memberTypes',
            ' '.join([_qname(m.name, m.schema, schema, context)
                      for m in union]))


def dump_simple_content(ct, schema, context):
    with TagGuard('simpleContent', context):
        with TagGuard('extension', context):
            qn = _qname(ct.text().type.name, ct.text().type.schema,
                        schema, context)
            context.add_attribute('base', qn)

            dump_attribute_uses(ct, ct.attribute_uses(), schema, context)


def dump_particle(ct, particle, schema, context, names, in_group=False):
    def dump_occurs_attributes():
        if particle.min_occurs != 1:
            context.add_attribute('minOccurs', particle.min_occurs)
        if particle.max_occurs != 1:
            context.add_attribute('maxOccurs',
                                  _max_occurs(particle.max_occurs))

    if not checks.is_particle(particle):
        return
    elif (checks.is_element(particle.term) and
            context.om.is_opaque_ct_member(ct, particle.term)):
        return
    elif (checks.is_compositor(particle.term) and
            all([context.om.is_opaque_ct_member(ct, p.term)
                 for p in particle.traverse() if checks.is_particle(p)])):
        return
    elif particle.term.schema != schema:
        groups = context.egroups.get(particle.term.schema, {})

        if particle.term in [t for t in groups.iterkeys()]:
            group_name = groups[particle.term].name
            with TagGuard('group', context):
                context.add_attribute(
                    'ref',
                    _qname(group_name, particle.term.schema, schema, context))

                dump_occurs_attributes()

            return

    name = _term_name(particle.term)
    with TagGuard(name, context):
        if not in_group:
            dump_occurs_attributes()

        if checks.is_compositor(particle.term):
            for p in particle.term.members:
                dump_particle(ct, p, schema, context, names)
        elif checks.is_element(particle.term):
            is_element_def = False
            if particle.term.schema == schema:
                top_elements = [e for e in particle.term.schema.elements]

                is_element_def = particle.term not in top_elements

            dump_element_attributes(particle.term, is_element_def,
                                    schema, context)

            if is_element_def:
                context.add_attribute(
                    'form',
                    'qualified' if particle.qualified else 'unqualified')
        elif checks.is_any(particle.term):
            _dump_any(particle.term, schema, context)
        else:  # pragma: no cover
            assert False


def dump_attribute_uses(ct, attr_uses, schema, context):
    for u in attr_uses:
        if (context.om.is_opaque_ct_member(ct, u.attribute) and
                not checks.is_single_valued_type(ct)):
            continue

        if checks.is_any(u.attribute):
            with TagGuard('anyAttribute', context):
                _dump_any(u.attribute, schema, context)
        else:
            dump_attribute_use(u, schema, context)


def dump_attribute_use(attr_use, schema, context):
    assert checks.is_attribute(attr_use.attribute)

    attribute = attr_use.attribute

    if not checks.is_xml_attribute(attribute) and attribute.schema != schema:
        # We reference attribute from other schema but since we don't
        # maintain top-level attributes we can reference then only
        # attribute group.
        groups = context.agroups[attribute.schema]
        group_name = groups[attribute].name
        with TagGuard('attributeGroup', context):
            context.add_attribute(
                'ref',
                _qname(group_name, attribute.schema, schema, context))

        return

    with TagGuard('attribute', context):
        if checks.is_xml_attribute(attribute):
            context.add_attribute(
                'ref', _qname(attribute.name, attribute.schema,
                              schema, context, prefix=XML_PREFIX))
        else:
            _dump_attribute_attributes(attribute, schema, context)

        if not checks.is_xml_attribute(attribute):
            # Attribute declaration cannot have both ref and form attributes.
            context.add_attribute(
                'form',
                'qualified' if attr_use.qualified else 'unqualified')

        if attr_use.constraint.fixed:
            assert attr_use.constraint.value is not None, \
                'Attribute has fixed value but the value itself is unknown'
            context.add_attribute('fixed',
                                  attr_use.constraint.value)
        elif attr_use.constraint.value is not None:
            context.add_attribute('default',
                                  attr_use.constraint.value)

        if attr_use.required:
            context.add_attribute('use', 'required')


def _dump_attribute_attributes(attribute, schema, context):
    assert checks.is_attribute(attribute)

    context.add_attribute(
        'name',
        _qname(attribute.name, attribute.schema, schema, context))

    if not checks.is_simple_urtype(attribute.type):
        context.add_attribute(
            'type', _qname(attribute.type.name, attribute.type.schema,
                           schema, context))


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
                'type', _qname(element.type.name, element.type.schema,
                               schema, context))

        if element.constraint.fixed:
            assert element.constraint.value, \
                'Element has fixed value but the value itself is unknown'
            context.add_attribute('fixed',
                                  element.constraint.value)
        elif element.constraint.value is not None:
            context.add_attribute('default',
                                  element.constraint.value)
    else:
        context.add_attribute(
            'ref',
            _qname(element.name, element.schema, schema, context))


def _dump_any(elem, schema, context):
    assert checks.is_any(elem)

    val = '##any'
    if not elem.constraints:
        val = '##any'
    elif (len(elem.constraints) == 1 and
          isinstance(elem.constraints[0], elements.Any.Not) and
          isinstance(elem.constraints[0].name, elements.Any.Name) and
          elem.constraints[0].name.ns == schema.target_ns and
          elem.constraints[0].name.tag is None):
        val = '##other'
    elif (len(elem.constraints) > 1 and
          all([isinstance(x, elements.Any.Name) and x.tag is None
               for x in elem.constraints])):
        val = ' '.join([x.ns for x in elem.constraints])
    else:
        # Issue a warning about impossibility to convert to XSD any.
        pass

    context.add_attribute('namespace', val)
