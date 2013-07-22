# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import any
import base
import checks
import sequence
import uses

import prv.attribute_group
import prv.complex_content
import prv.group
import prv.simple_content
import prv.utils


def _has_duplicate_attributes(attrs):
    attrnames = []
    attrset = {}
    for a in attrs:
        if checks.is_any(a.attribute):
            continue

        name = '{0}:{1}'.format(
            'xml' if checks.is_xmlattribute(a.attribute)
            else a.attribute.schema.target_ns, a.attribute.name)
        attrnames.append((name, a))
        attrset[name] = a

    return len(attrnames) != len(attrset)


class ComplexType(base.SchemaBase):
    def __init__(self, attrs, parent_schema):
        super(ComplexType, self).__init__(attrs, parent_schema)

        self.name = self.attr('name')
        self.attributes = []
        self.term = None
        self.text = None

    @staticmethod
    def urtype(factory):
        urtype = ComplexType({'mixed': 'true'}, None)
        urtype.name = 'anyType'

        seqpart = uses.Particle({}, sequence.Sequence({}, None), factory)

        anypart = uses.Particle({}, any.Any({}, None), factory)
        anypart.max_occurs = base.UNBOUNDED

        anyattr = uses.AttributeUse({}, any.Any({}, None), factory)

        seqpart.element.children.append(anypart)
        urtype.children.append(seqpart)
        urtype.children.append(anyattr)

        urtype.finalize(factory)

        return urtype

    @property
    def mixed(self):
        return (self.term is not None and
                self.text is not None)

    @method_once
    def finalize(self, factory):
        mixed = self.attr('mixed') == 'true' or self.attr('mixed') == '1'

        for c in self.children:
            if isinstance(c, prv.simple_content.SimpleContent):
                assert self.term is None, 'Content model overriden'
                c.finalize(factory)
                self.text = base.SchemaText(c.base)
                self.attributes.extend(c.attributes)
            elif isinstance(c, prv.complex_content.ComplexContent):
                assert self.term is None, 'Content model overriden'
                c.finalize(factory)
                self.term = c.term
                self.attributes.extend(c.attributes)
                if c.mixed is not None:
                    mixed = c.mixed
            elif (checks.is_particle(c) and
                  (checks.is_compositor(c.element) or
                   isinstance(c.element, prv.group.Group))):
                assert self.term is None, 'Content model overriden'
                tmp = c.element.finalize(factory)
                if isinstance(c.element, prv.group.Group):
                    c.element = tmp.body
                else:
                    c.element = tmp
                self.term = c
            elif isinstance(c, prv.attribute_group.AttributeGroup):
                c.finalize(factory)
                self.attributes.extend(c.attributes)
            elif (checks.is_attribute_use(c) and
                  (checks.is_attribute(c.attribute) or
                   checks.is_any(c.attribute))):
                c.attribute = c.attribute.finalize(factory)
                self.attributes.append(c)
            else:
                assert False, 'Wrong content of ComplexType'

        if mixed:
            if self.term is None:
                self.term = uses.Particle(
                    {}, sequence.Sequence({}, self.schema), factory)
                self.term.element.finalize(factory)

            self.text = base.SchemaText(factory.simple_types['string'])

        assert not _has_duplicate_attributes(self.attributes), \
            'Duplicate attributes in CT in {0}'.format(self.schema.path)

        def attr_key(attr):
            if checks.is_any(attr.attribute):
                return ('', '')
            elif attr.attribute.schema is None:
                return ('~~~', attr.attribute.name)
            elif attr.attribute.schema != self.schema:
                return (attr.attribute.schema.prefix, attr.attribute.name)
            return ('', attr.attribute.name)
        self.attributes.sort(key=attr_key, reverse=True)

        return super(ComplexType, self).finalize(None)

    @method_once
    def nameit(self, parents, factory, names):
        prv.utils.forge_name(self, parents, factory, names)

        if self.term is not None:
            self.term.nameit(parents + [self], factory, names)
            assert self.term.name is not None, 'Name cannot be None'
