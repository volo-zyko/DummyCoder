# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import dumco.schema.base
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

    @method_once
    def finalize(self, factory):
        mixed = self.attr('mixed') == 'true' or self.attr('mixed') == '1'

        for c in self.children:
            if isinstance(c, xsd_simple_content.XsdSimpleContent):
                assert self.schema_element.particle is None, \
                    'Content model overriden'
                c.finalize(factory)
                self.schema_element.text = dumco.schema.base.SchemaText(c.base)
                self.schema_element.attributes.extend(c.attributes)
            elif isinstance(c, xsd_complex_content.XsdComplexContent):
                assert self.schema_element.particle is None, \
                    'Content model overriden'
                c.finalize(factory)
                self.schema_element.particle = c.particle
                self.schema_element.attributes.extend(c.attributes)
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
                c.finalize(factory)
                self.schema_element.attributes.extend(c.attributes)
            elif (isinstance(c, xsd_attribute.XsdAttribute) or
                  isinstance(c, xsd_any.XsdAny)):
                self.schema_element.attributes.append(c.finalize(factory))
            else: # pragma: no cover
                assert False, 'Wrong content of ComplexType'

        if mixed:
            if self.schema_element.particle is None:
                self.schema_element.particle = dumco.schema.uses.Particle(1, 1,
                    dumco.schema.elements.Sequence(self.schema_element.schema))

            self.schema_element.text = dumco.schema.base.SchemaText(
                dumco.schema.base.xsd_builtin_types()['string'])

        assert not _has_duplicate_attributes(self.schema_element.attributes), \
            'Duplicate attributes in CT in {}'.format(
                self.schema_element.schema.path)

        def attr_key(attr):
            if dumco.schema.checks.is_any(attr.attribute):
                return ('', '')
            elif attr.attribute.schema is None:
                return ('~~~', attr.attribute.name)
            elif attr.attribute.schema != self.schema_element.schema:
                return (attr.attribute.schema.prefix, attr.attribute.name)
            return ('', attr.attribute.name)
        self.schema_element.attributes.sort(key=attr_key, reverse=True)

        return self.schema_element


def _has_duplicate_attributes(attrs):
    attrnames = []
    attrset = {}
    for a in attrs:
        if dumco.schema.checks.is_any(a.attribute):
            continue

        name = '{}:{}'.format(
            'xml' if dumco.schema.checks.is_xmlattribute(a.attribute)
            else a.attribute.schema.target_ns, a.attribute.name)
        attrnames.append((name, a))
        attrset[name] = a

    return len(attrnames) != len(attrset)
