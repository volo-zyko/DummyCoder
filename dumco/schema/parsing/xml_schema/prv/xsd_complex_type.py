# Distributed under the GPLv2 License; see accompanying file COPYING.

import copy

from dumco.utils.decorators import method_once

import dumco.schema.checks
import dumco.schema.model
import dumco.schema.uses
import dumco.schema.xsd_types

import base
import utils
import xsd_all
import xsd_any_attribute
import xsd_attribute
import xsd_attribute_group
import xsd_choice
import xsd_complex_content
import xsd_group
import xsd_sequence
import xsd_simple_content


def xsd_complexType(attrs, parent, factory, schema_path, all_schemata):
    name = factory.get_attribute(attrs, 'name', default=None)

    mixed = factory.get_attribute(attrs, 'mixed', default=False)
    mixed = (mixed == 'true' or mixed == '1')

    abstract = factory.get_attribute(attrs, 'abstract', default=False)
    abstract = (abstract == 'true' or abstract == '1')

    ct = dumco.schema.model.ComplexType(name,
                                        all_schemata[schema_path].dom_element)

    new_element = XsdComplexType(ct, mixed=mixed, abstract=abstract)
    parent.children.append(new_element)

    factory.add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                                 'complex_types', is_type=True)

    return (new_element, {
        'all': xsd_all.xsd_all,
        'annotation': factory.xsd_annotation,
        'anyAttribute': xsd_any_attribute.xsd_anyAttribute,
        'attribute': xsd_attribute.xsd_attribute,
        'attributeGroup': xsd_attribute_group.xsd_attributeGroup,
        'choice': xsd_choice.xsd_choice,
        'complexContent': xsd_complex_content.xsd_complexContent,
        'group': xsd_group.xsd_group,
        'sequence': xsd_sequence.xsd_sequence,
        'simpleContent': xsd_simple_content.xsd_simpleContent,
    })


class XsdComplexType(base.XsdBase):
    def __init__(self, ct, mixed=False, abstract=False):
        super(XsdComplexType, self).__init__()

        self.dom_element = ct
        self.mixed = mixed
        self.abstract = abstract
        self.name = ct.name

    @method_once
    def finalize(self, factory):
        attr_uses = []
        particle = None
        text = None
        mixed = self.mixed

        for c in self.children:
            if isinstance(c, xsd_simple_content.XsdSimpleContent):
                assert particle is None, 'Content model overridden'
                (content_type, sub_attr_uses) = c.finalize(factory)
                text = dumco.schema.uses.SchemaText(content_type)
                attr_uses.extend(sub_attr_uses)
            elif isinstance(c, xsd_complex_content.XsdComplexContent):
                assert particle is None, 'Content model overridden'
                (particle, sub_attr_uses) = c.finalize(factory)
                attr_uses.extend(sub_attr_uses)
                if c.mixed is not None:
                    mixed = c.mixed
            elif (isinstance(c, xsd_all.XsdAll) or
                  isinstance(c, xsd_choice.XsdChoice) or
                  isinstance(c, xsd_sequence.XsdSequence) or
                  isinstance(c, xsd_group.XsdGroup)):
                assert particle is None, 'Content model overridden'
                particle = c.finalize(factory)
            elif isinstance(c, xsd_attribute_group.XsdAttributeGroup):
                attr_uses.extend(c.finalize(factory))
            elif isinstance(c, xsd_attribute.XsdAttribute):
                if not c.prohibited:
                    attr_uses.append(c.finalize(factory))
            elif isinstance(c, xsd_any_attribute.XsdAnyAttribute):
                attr_uses.append(c.finalize(factory))
            else:  # pragma: no cover
                assert False, 'Wrong content of ComplexType'

        if (dumco.schema.checks.is_particle(particle) and
                dumco.schema.checks.is_terminal(particle.term)):
            seq = dumco.schema.model.Sequence()
            seq.members.append(particle)

            particle = dumco.schema.uses.Particle(1, 1, seq)

        if mixed:
            if particle is None:
                particle = dumco.schema.uses.Particle(
                    1, 1, dumco.schema.model.Sequence())

            text = dumco.schema.uses.SchemaText(
                dumco.schema.xsd_types.xsd_builtin_types()['string'])

        _assert_on_duplicate_attributes(attr_uses, self)

        if attr_uses or text is not None:
            if particle is None:
                particle = dumco.schema.uses.Particle(
                    1, 1, dumco.schema.model.Sequence())
            else:
                new_particle = copy.copy(particle)
                new_particle.term = copy.copy(particle.term)
                new_particle.term.members = copy.copy(particle.term.members)
                particle = new_particle

        if attr_uses:
            particle.term.members[0:0] = attr_uses
        if text is not None:
            particle.term.members.append(text)

        self.dom_element.structure = particle

        return self.dom_element

    def dump(self, context):
        with utils.XsdTagGuard('complexType', context):
            context.add_attribute('name', self.dom_element.name)

            if self.dom_element.mixed:
                context.add_attribute('mixed', 'true')

            for c in self.children:
                c.dump(context)


def _assert_on_duplicate_attributes(attr_uses, ct):
    attrset = {}
    for a in attr_uses:
        if dumco.schema.checks.is_any(a.attribute):
            continue

        name = '{}:{}'.format(
            'xml' if dumco.schema.checks.is_xml_attribute(a.attribute)
            else a.attribute.schema.target_ns, a.attribute.name)

        assert name not in attrset, \
            'Duplicate attribute {} in CT {} in {}.xsd'.format(
                a.attribute.name, ct.dom_element.name,
                ct.dom_element.schema.filename)

        attrset[name] = a
