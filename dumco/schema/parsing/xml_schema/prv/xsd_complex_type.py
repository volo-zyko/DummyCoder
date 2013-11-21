# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.base
import dumco.schema.checks
import dumco.schema.elements
import dumco.schema.uses

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
        attribute_uses = self.schema_element.attribute_uses

        mixed = self.attr('mixed') == 'true' or self.attr('mixed') == '1'

        for c in self.children:
            if isinstance(c, xsd_simple_content.XsdSimpleContent):
                assert self.schema_element.particle is None, \
                    'Content model overriden'
                c.finalize(factory)
                self.schema_element.text = \
                    dumco.schema.base.SchemaText(c.content_type)
                attribute_uses.extend(c.attr_uses)
            elif isinstance(c, xsd_complex_content.XsdComplexContent):
                assert self.schema_element.particle is None, \
                    'Content model overriden'
                c.finalize(factory)
                self.schema_element.particle = c.particle
                attribute_uses.extend(c.attr_uses)
                if c.mixed is not None:
                    mixed = c.mixed
            elif (isinstance(c, xsd_all.XsdAll) or
                  isinstance(c, xsd_choice.XsdChoice) or
                  isinstance(c, xsd_sequence.XsdSequence) or
                  isinstance(c, xsd_group.XsdGroup)):
                assert self.schema_element.particle is None, \
                    'Content model overriden'
                self.schema_element.particle = c.finalize(factory)
            elif isinstance(c, xsd_attribute_group.XsdAttributeGroup):
                attribute_uses.extend(c.finalize(factory).attr_uses)
            elif isinstance(c, xsd_attribute.XsdAttribute):
                if not c.prohibited:
                    attribute_uses.append(c.finalize(factory))
            elif isinstance(c, xsd_any.XsdAny):
                attribute_uses.append(c.finalize(factory))
            else: # pragma: no cover
                assert False, 'Wrong content of ComplexType'

        if mixed:
            if self.schema_element.particle is None:
                self.schema_element.particle = dumco.schema.uses.Particle(
                    None, None, 1, 1,
                    dumco.schema.elements.Sequence(self.schema_element.schema))

            self.schema_element.text = dumco.schema.base.SchemaText(
                dumco.schema.base.xsd_builtin_types()['string'])

        assert not _has_duplicate_attributes(attribute_uses), \
            'Duplicate attributes in CT in {}'.format(
                self.schema_element.schema.path)

        def attr_key(use):
            checks = dumco.schema.checks
            if dumco.schema.checks.is_any(use.attribute):
                return (0, '')
            elif use.attribute.schema is None:
                return (-2, use.attribute.name)
            elif checks.is_xml_namespace(use.attribute.schema.target_ns):
                return (-3, use.attribute.name)
            elif use.attribute.schema != self.schema_element.schema:
                num = sum([ord(c) for c in use.attribute.schema.prefix])
                return (-4 - num, use.attribute.name)
            return (-1, use.attribute.name)
        attribute_uses.sort(key=attr_key)

        return self.schema_element


def _has_duplicate_attributes(attrs):
    attrnames = []
    attrset = {}
    for a in attrs:
        if dumco.schema.checks.is_any(a.attribute):
            continue

        name = '{}:{}'.format(
            'xml' if dumco.schema.checks.is_xml_attribute(a.attribute)
            else a.attribute.schema.target_ns, a.attribute.name)
        attrnames.append((name, a))
        attrset[name] = a

    return len(attrnames) != len(attrset)
