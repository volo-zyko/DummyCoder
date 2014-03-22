# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.checks
import dumco.schema.elements
import dumco.schema.uses
import dumco.schema.xsd_types

import xsd_all
import xsd_any
import xsd_attribute
import xsd_attribute_group
import xsd_base
import xsd_choice
import xsd_complex_content
import xsd_group
import xsd_sequence
import xsd_simple_content


def xsd_complexType(attrs, parent_element, factory, schema_path, all_schemata):
    new_element = XsdComplexType(attrs, all_schemata[schema_path])
    parent_element.children.append(new_element)

    factory.add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                                 'complex_types', is_type=True)

    return (new_element, {
        'all': xsd_all.xsd_all,
        'annotation': factory.xsd_annotation,
        'anyAttribute': xsd_any.xsd_anyAttribute,
        'attribute': xsd_attribute.xsd_attribute,
        'attributeGroup': xsd_attribute_group.xsd_attributeGroup,
        'choice': xsd_choice.xsd_choice,
        'complexContent': xsd_complex_content.xsd_complexContent,
        'group': xsd_group.xsd_group,
        'sequence': xsd_sequence.xsd_sequence,
        'simpleContent': xsd_simple_content.xsd_simpleContent,
    })


class XsdComplexType(xsd_base.XsdBase):
    def __init__(self, attrs, parent_schema):
        super(XsdComplexType, self).__init__(attrs)

        self.schema_element = dumco.schema.elements.ComplexType(
            self.attr('name'), parent_schema.schema_element)

        self.abstract = (self.attr('abstract') == 'true' or
                         self.attr('abstract') == '1')

    @method_once
    def finalize(self, factory):
        attr_uses = []
        particle = None
        text = None

        mixed = self.attr('mixed') == 'true' or self.attr('mixed') == '1'

        for c in self.children:
            if isinstance(c, xsd_simple_content.XsdSimpleContent):
                assert particle is None, 'Content model overridden'
                c.finalize(factory)
                text = dumco.schema.elements.SchemaText(c.content_type)
                attr_uses.extend(c.attr_uses)
            elif isinstance(c, xsd_complex_content.XsdComplexContent):
                assert particle is None, 'Content model overridden'
                c.finalize(factory)
                particle = c.part
                attr_uses.extend(c.attr_uses)
                if c.mixed is not None:
                    mixed = c.mixed
            elif (isinstance(c, xsd_all.XsdAll) or
                  isinstance(c, xsd_choice.XsdChoice) or
                  isinstance(c, xsd_sequence.XsdSequence) or
                  isinstance(c, xsd_group.XsdGroup)):
                assert particle is None, 'Content model overridden'
                particle = c.finalize(factory)
            elif isinstance(c, xsd_attribute_group.XsdAttributeGroup):
                attr_uses.extend(c.finalize(factory).attr_uses)
            elif isinstance(c, xsd_attribute.XsdAttribute):
                if not c.prohibited:
                    attr_uses.append(c.finalize(factory))
            elif isinstance(c, xsd_any.XsdAny):
                attr_uses.append(c.finalize(factory))
            else:  # pragma: no cover
                assert False, 'Wrong content of ComplexType'

        if mixed:
            if particle is None:
                particle = dumco.schema.uses.Particle(
                    False, 1, 1,
                    dumco.schema.elements.Sequence(self.schema_element.schema))

            text = dumco.schema.elements.SchemaText(
                dumco.schema.xsd_types.xsd_builtin_types()['string'])

        _assert_on_duplicate_attributes(attr_uses, self)

        def attr_key(use):
            if dumco.schema.checks.is_any(use.attribute):
                return (0, '')
            elif use.attribute.schema is None:
                return (-2, use.attribute.name)
            elif use.attribute.schema != self.schema_element.schema:
                num = sum([ord(c) for c in use.attribute.schema.prefix])
                return (-3 - num, use.attribute.name)
            return (-1, use.attribute.name)
        attr_uses.sort(key=attr_key)

        if attr_uses or text is not None:
            root = dumco.schema.uses.Particle(
                False, 1, 1,
                dumco.schema.elements.Sequence(self.schema_element.schema))
            root.term.members.extend(attr_uses)
            if particle is not None:
                root.term.members.append(particle)
            if text is not None:
                root.term.members.append(text)
            self.schema_element.structure = root
        else:
            self.schema_element.structure = particle

        return self.schema_element


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
                a.attribute.name, ct.schema_element.name,
                ct.schema_element.schema.filename)

        attrset[name] = a
