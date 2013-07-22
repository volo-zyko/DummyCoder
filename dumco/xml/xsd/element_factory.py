# Distributed under the GPLv2 License; see accompanying file COPYING.

import os.path

import dumco.schema.all
import dumco.schema.any
import dumco.schema.attribute
import dumco.schema.base
import dumco.schema.choice
import dumco.schema.complex_type
import dumco.schema.element
import dumco.schema.restriction
import dumco.schema.schema
import dumco.schema.sequence
import dumco.schema.simple_type
import dumco.schema.checks
import dumco.schema.uses

import dumco.schema.prv.attribute_group
import dumco.schema.prv.complex_content
import dumco.schema.prv.enumeration
import dumco.schema.prv.extension_cc
import dumco.schema.prv.extension_sc
import dumco.schema.prv.group
import dumco.schema.prv.list
import dumco.schema.prv.restriction_cc
import dumco.schema.prv.restriction_sc
import dumco.schema.prv.simple_content
import dumco.schema.prv.union


def _add_to_parent_schema(element, attrs, schema, fieldname,
                          factory, parents=None, is_type=False):
    try:
        name = factory.get_attribute(attrs, 'name')
        assert name is not None, 'Name cannot be None'

        elements = getattr(schema, fieldname)
        elements[name] = element
    except LookupError:
        if is_type:
            assert parents is not None, 'parents should be a list'
            schema.unnamed_types.append((list(parents), element))


class XsdElementFactory(object):
    def __init__(self, element_namer):
        # Internals of this factory.
        self.dispatcher_stack = []
        self.dispatcher = {
            'schema': XsdElementFactory._xsd_schema,
        }
        self.namespaces = {'xml': dumco.schema.checks.XML_NAMESPACE}
        self.all_named_ns = {dumco.schema.checks.XML_NAMESPACE: 'xml'}
        self.parents = []

        # Part of the factorie's interface.
        self.namer = element_namer
        self.extension = '.xsd'

        self.simple_types = {x: dumco.schema.base.XsdNativeType(x)
                             for x in dumco.schema.base.NATIVE_XSD_TYPE_NAMES}

        self.xml_attributes = {x: dumco.schema.base.XmlAttribute(x)
                               for x in ['base', 'id', 'lang', 'space']}

        self.complex_urtype = dumco.schema.complex_type.ComplexType.urtype(self)
        self.simple_urtype = dumco.schema.simple_type.SimpleType.urtype(self)

    def open_namespace(self, prefix, uri):
        self.namespaces[prefix] = uri

        if prefix is not None and not dumco.schema.checks.is_xsd_namespace(uri):
            assert (not self.all_named_ns.has_key(uri) or
                    self.all_named_ns[uri] == prefix), \
                'Namespace prefix {0} is already defined as {1}'.format(
                    prefix, self.all_named_ns[uri])
            self.all_named_ns[uri] = prefix

    def close_namespace(self, prefix):
        assert self.namespaces.has_key(prefix), \
            'Closing non-existent namespace'
        del self.namespaces[prefix]

    def new_element(self, name, attrs, parent_element,
                    schema_path, all_schemata):
        # Here we don't support anything non-XSD.
        assert name[0] == dumco.schema.checks.XSD_NAMESPACE, \
            'Uknown elment {0}:{1}'.format(name[0], name[1])

        self.dispatcher_stack.append(self.dispatcher)

        assert self.dispatcher.has_key(name[1]), \
            '"{0}" is not supported in {1}'.format(
                name[1], parent_element.__class__.__name__)

        (element, self.dispatcher) = self.dispatcher[name[1]](
            self, attrs, parent_element, schema_path, all_schemata)

        try:
            self.parents.append(element[1])
            return element[0]
        except TypeError:
            self.parents.append(element)
            return element

    def finalize_element(self, element):
        self.dispatcher = self.dispatcher_stack.pop()
        self.parents.pop()

    def element_append_text(self, element, text):
        element.append_doc(text)

    def finalize_documents(self, all_schemata):
        for schema in all_schemata.itervalues():
            schema.set_imports(all_schemata)

            if self.all_named_ns.has_key(schema.target_ns):
                schema.set_namespace(self.all_named_ns[schema.target_ns],
                                     schema.target_ns)

        for schema in all_schemata.itervalues():
            schema.finalize(all_schemata, self)

        for schema in all_schemata.itervalues():
            schema.cleanup()

    def get_attribute(self, attrs, localname, uri=None):
        if not attrs.has_key((uri, localname)):
            raise LookupError
        return attrs.get((uri, localname))

    def _noop_handler(self, attrs, parent_element,
                      schema_path, all_schemata):
        return (parent_element, {
            'documentation': XsdElementFactory._noop_handler,
            'field': XsdElementFactory._noop_handler,
            'selector': XsdElementFactory._noop_handler,
        })

    def _xsd_all(self, attrs, parent_element,
                 schema_path, all_schemata):
        new_element = dumco.schema.all.All(
            attrs, all_schemata[schema_path])
        particle = dumco.schema.uses.Particle(attrs, new_element, self)
        parent_element.children.append(particle)

        return ((new_element, particle), {
            'annotation': XsdElementFactory._noop_handler,
            'element': XsdElementFactory._xsd_element,
        })

    def _xsd_annotation(self, attrs, parent_element,
                        schema_path, all_schemata):
        return (parent_element, {
            'documentation': XsdElementFactory._xsd_documentation,
        })

    def _xsd_any(self, attrs, parent_element,
                 schema_path, all_schemata):
        new_element = dumco.schema.any.Any(
            attrs, all_schemata[schema_path])
        particle = dumco.schema.uses.Particle(attrs, new_element, self)
        parent_element.children.append(particle)

        return ((new_element, particle), {
            'annotation': XsdElementFactory._noop_handler,
        })

    def _xsd_anyAttribute(self, attrs, parent_element,
                          schema_path, all_schemata):
        new_element = dumco.schema.any.Any(
            attrs, all_schemata[schema_path])
        attribute_use = dumco.schema.uses.AttributeUse(attrs, new_element, self)
        parent_element.children.append(attribute_use)

        return (new_element, {
            'annotation': XsdElementFactory._noop_handler,
        })

    def _xsd_attribute(self, attrs, parent_element,
                       schema_path, all_schemata):
        new_element = dumco.schema.attribute.Attribute(
            attrs, all_schemata[schema_path])
        attribute_use = dumco.schema.uses.AttributeUse(attrs, new_element, self)
        parent_element.children.append(attribute_use)

        _add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                              'attributes', self)

        return (new_element, {
            'annotation': XsdElementFactory._xsd_annotation,
            'simpleType': XsdElementFactory._xsd_simpleType,
        })

    def _xsd_attributeGroup(self, attrs, parent_element,
                            schema_path, all_schemata):
        new_element = dumco.schema.prv.attribute_group.AttributeGroup(
            attrs, all_schemata[schema_path])
        parent_element.children.append(new_element)

        _add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                              'attribute_groups', self)

        return (new_element, {
            'annotation': XsdElementFactory._noop_handler,
            'anyAttribute': XsdElementFactory._xsd_anyAttribute,
            'attribute': XsdElementFactory._xsd_attribute,
            'attributeGroup': XsdElementFactory._xsd_attributeGroup,
        })

    def _xsd_choice(self, attrs, parent_element,
                    schema_path, all_schemata):
        new_element = dumco.schema.choice.Choice(
            attrs, all_schemata[schema_path])
        particle = dumco.schema.uses.Particle(attrs, new_element, self)
        parent_element.children.append(particle)

        return ((new_element, particle), {
            'annotation': XsdElementFactory._noop_handler,
            'any': XsdElementFactory._xsd_any,
            'choice': XsdElementFactory._xsd_choice,
            'element': XsdElementFactory._xsd_element,
            'group': XsdElementFactory._xsd_group,
            'sequence': XsdElementFactory._xsd_sequence,
        })

    def _xsd_complexContent(self, attrs, parent_element,
                            schema_path, all_schemata):
        new_element = dumco.schema.prv.complex_content.ComplexContent(
            attrs, all_schemata[schema_path])
        parent_element.children.append(new_element)

        return (new_element, {
            'annotation': XsdElementFactory._noop_handler,
            'extension': XsdElementFactory._xsd_extension_in_complexContent,
            'restriction': XsdElementFactory._xsd_restriction_in_complexContent,
        })

    def _xsd_complexType(self, attrs, parent_element,
                         schema_path, all_schemata):
        new_element = dumco.schema.complex_type.ComplexType(
            attrs, all_schemata[schema_path])
        parent_element.children.append(new_element)

        _add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                              'complex_types', self, parents=self.parents,
                              is_type=True)

        return (new_element, {
            'all': XsdElementFactory._xsd_all,
            'annotation': XsdElementFactory._xsd_annotation,
            'anyAttribute': XsdElementFactory._xsd_anyAttribute,
            'attribute': XsdElementFactory._xsd_attribute,
            'attributeGroup': XsdElementFactory._xsd_attributeGroup,
            'choice': XsdElementFactory._xsd_choice,
            'complexContent': XsdElementFactory._xsd_complexContent,
            'group': XsdElementFactory._xsd_group,
            'sequence': XsdElementFactory._xsd_sequence,
            'simpleContent': XsdElementFactory._xsd_simpleContent,
        })

    def _xsd_documentation(self, attrs, parent_element,
                           schema_path, all_schemata):
        return (parent_element, None)

    def _xsd_element(self, attrs, parent_element, schema_path, all_schemata):
        new_element = dumco.schema.element.Element(
            attrs, all_schemata[schema_path])
        particle = dumco.schema.uses.Particle(attrs, new_element, self)
        parent_element.children.append(particle)

        _add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                              'elements', self)

        return (new_element, {
            'annotation': XsdElementFactory._xsd_annotation,
            'complexType': XsdElementFactory._xsd_complexType,
            'key': XsdElementFactory._noop_handler,
            'keyref': XsdElementFactory._noop_handler,
            'simpleType': XsdElementFactory._xsd_simpleType,
            'unique': XsdElementFactory._noop_handler,
        })

    def _xsd_enumeration(self, attrs, parent_element,
                         schema_path, all_schemata):
        new_element = dumco.schema.prv.enumeration.Enumeration(
            attrs, all_schemata[schema_path])
        parent_element.enumeration.append(new_element)

        return (new_element, {
            'annotation': XsdElementFactory._xsd_annotation,
        })

    @staticmethod
    def _xsd_extension_in_complexContent(self, attrs, parent_element,
                                         schema_path, all_schemata):
        new_element = dumco.schema.prv.extension_cc.ComplexExtension(
            attrs, all_schemata[schema_path])
        parent_element.children.append(new_element)

        return (new_element, {
            'all': XsdElementFactory._xsd_all,
            'annotation': XsdElementFactory._noop_handler,
            'anyAttribute': XsdElementFactory._xsd_anyAttribute,
            'attribute': XsdElementFactory._xsd_attribute,
            'attributeGroup': XsdElementFactory._xsd_attributeGroup,
            'choice': XsdElementFactory._xsd_choice,
            'group': XsdElementFactory._xsd_group,
            'sequence': XsdElementFactory._xsd_sequence,
        })

    @staticmethod
    def _xsd_extension_in_simpleContent(self, attrs, parent_element,
                                        schema_path, all_schemata):
        new_element = dumco.schema.prv.extension_sc.SimpleExtension(
            attrs, all_schemata[schema_path])
        parent_element.children.append(new_element)

        return (new_element, {
            'annotation': XsdElementFactory._noop_handler,
            'anyAttribute': XsdElementFactory._xsd_anyAttribute,
            'attribute': XsdElementFactory._xsd_attribute,
            'attributeGroup': XsdElementFactory._xsd_attributeGroup,
        })

    def _xsd_group(self, attrs, parent_element,
                   schema_path, all_schemata):
        new_element = dumco.schema.prv.group.Group(
            attrs, all_schemata[schema_path])
        particle = dumco.schema.uses.Particle(attrs, new_element, self)
        parent_element.children.append(particle)

        _add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                              'groups', self)

        return ((new_element, particle), {
            'all': XsdElementFactory._xsd_all,
            'annotation': XsdElementFactory._noop_handler,
            'choice': XsdElementFactory._xsd_choice,
            'sequence': XsdElementFactory._xsd_sequence,
        })

    def _xsd_import(self, attrs, parent_element,
                    schema_path, all_schemata):
        try:
            location = self.get_attribute(attrs, 'schemaLocation')
        except LookupError:
            return (parent_element, None)

        namespace = self.get_attribute(attrs, 'namespace')

        assert (namespace is not None and location is not None), \
            'Cannot import XSD document in {0}'.format(schema_path)

        new_schema_path = os.path.realpath(
            os.path.join(os.path.dirname(schema_path), location))
        assert os.path.isfile(new_schema_path), \
            'File {0} does not exist'.format(new_schema_path)

        all_schemata[new_schema_path] = all_schemata[new_schema_path] \
            if new_schema_path in all_schemata else None
        all_schemata[schema_path].imports[new_schema_path] = None

        return (parent_element, {
            'annotation': XsdElementFactory._noop_handler,
        })

    def _xsd_length(self, attrs, parent_element,
                    schema_path, all_schemata):
        parent_element.length = self.get_attribute(attrs, 'value')

        return (parent_element, {
            'annotation': XsdElementFactory._noop_handler,
        })

    def _xsd_list(self, attrs, parent_element,
                  schema_path, all_schemata):
        new_element = dumco.schema.prv.list.List(
            attrs, all_schemata[schema_path])
        parent_element.children.append(new_element)

        return (new_element, {
            'annotation': XsdElementFactory._noop_handler,
            'simpleType': XsdElementFactory._xsd_simpleType,
        })

    def _xsd_maxExclusive(self, attrs, parent_element,
                          schema_path, all_schemata):
        parent_element.max_exclusive = self.get_attribute(attrs, 'value')

        return (parent_element, {
            'annotation': XsdElementFactory._noop_handler,
        })

    def _xsd_maxInclusive(self, attrs, parent_element,
                          schema_path, all_schemata):
        parent_element.max_inclusive = self.get_attribute(attrs, 'value')

        return (parent_element, {
            'annotation': XsdElementFactory._noop_handler,
        })

    def _xsd_maxLength(self, attrs, parent_element,
                       schema_path, all_schemata):
        parent_element.max_length = self.get_attribute(attrs, 'value')

        return (parent_element, {
            'annotation': XsdElementFactory._noop_handler,
        })

    def _xsd_minExclusive(self, attrs, parent_element,
                          schema_path, all_schemata):
        parent_element.min_exclusive = self.get_attribute(attrs, 'value')

        return (parent_element, {
            'annotation': XsdElementFactory._noop_handler,
        })

    def _xsd_minInclusive(self, attrs, parent_element,
                          schema_path, all_schemata):
        parent_element.min_inclusive = self.get_attribute(attrs, 'value')

        return (parent_element, {
            'annotation': XsdElementFactory._noop_handler,
        })

    def _xsd_minLength(self, attrs, parent_element,
                       schema_path, all_schemata):
        parent_element.min_length = self.get_attribute(attrs, 'value')

        return (parent_element, {
            'annotation': XsdElementFactory._noop_handler,
        })

    def _xsd_pattern(self, attrs, parent_element,
                     schema_path, all_schemata):
        parent_element.pattern = self.get_attribute(attrs, 'value')

        return (parent_element, {
            'annotation': XsdElementFactory._noop_handler,
        })

    def _xsd_restriction(self, attrs, parent_element,
                         schema_path, all_schemata):
        new_element = dumco.schema.restriction.Restriction(
            attrs, all_schemata[schema_path])
        parent_element.children.append(new_element)

        return (new_element, {
            'annotation': XsdElementFactory._noop_handler,
            'enumeration': XsdElementFactory._xsd_enumeration,
            'length': XsdElementFactory._xsd_length,
            'maxExclusive': XsdElementFactory._xsd_maxExclusive,
            'maxInclusive': XsdElementFactory._xsd_maxInclusive,
            'maxLength': XsdElementFactory._xsd_maxLength,
            'minExclusive': XsdElementFactory._xsd_minExclusive,
            'minInclusive': XsdElementFactory._xsd_minInclusive,
            'minLength': XsdElementFactory._xsd_minLength,
            'pattern': XsdElementFactory._xsd_pattern,
            'simpleType': XsdElementFactory._xsd_simpleType,
        })

    def _xsd_restriction_in_complexContent(self, attrs, parent_element,
                                           schema_path, all_schemata):
        new_element = dumco.schema.prv.restriction_cc.ComplexRestriction(
            attrs, all_schemata[schema_path])
        parent_element.children.append(new_element)

        return (new_element, {
            'all': XsdElementFactory._xsd_all,
            'annotation': XsdElementFactory._noop_handler,
            'anyAttribute': XsdElementFactory._xsd_anyAttribute,
            'attribute': XsdElementFactory._xsd_attribute,
            'attributeGroup': XsdElementFactory._xsd_attributeGroup,
            'choice': XsdElementFactory._xsd_choice,
            'group': XsdElementFactory._xsd_group,
            'sequence': XsdElementFactory._xsd_sequence,
        })

    def _xsd_restriction_in_simpleContent(self, attrs, parent_element,
                                          schema_path, all_schemata):
        new_element = dumco.schema.prv.restriction_sc.SimpleRestriction(
            attrs, all_schemata[schema_path])
        parent_element.children.append(new_element)

        return (new_element, {
            'annotation': XsdElementFactory._noop_handler,
            'anyAttribute': XsdElementFactory._xsd_anyAttribute,
            'attribute': XsdElementFactory._xsd_attribute,
            'attributeGroup': XsdElementFactory._xsd_attributeGroup,
            'enumeration': XsdElementFactory._xsd_enumeration,
            'length': XsdElementFactory._xsd_length,
            'maxExclusive': XsdElementFactory._xsd_maxExclusive,
            'maxInclusive': XsdElementFactory._xsd_maxInclusive,
            'maxLength': XsdElementFactory._xsd_maxLength,
            'minExclusive': XsdElementFactory._xsd_minExclusive,
            'minInclusive': XsdElementFactory._xsd_minInclusive,
            'minLength': XsdElementFactory._xsd_minLength,
            'pattern': XsdElementFactory._xsd_pattern,
            'simpleType': XsdElementFactory._xsd_simpleType,
        })

    def _xsd_schema(self, attrs, parent_element,
                    schema_path, all_schemata):
        schema = dumco.schema.schema.Schema(attrs, schema_path)
        all_schemata[schema_path] = schema
        for (prefix, uri) in self.namespaces.iteritems():
            schema.set_namespace(prefix, uri)

        return (schema, {
            'annotation': XsdElementFactory._noop_handler,
            'attribute': XsdElementFactory._xsd_attribute,
            'attributeGroup': XsdElementFactory._xsd_attributeGroup,
            'complexType': XsdElementFactory._xsd_complexType,
            'element': XsdElementFactory._xsd_element,
            'group': XsdElementFactory._xsd_group,
            'import': XsdElementFactory._xsd_import,
            'notation': XsdElementFactory._noop_handler,
            'simpleType': XsdElementFactory._xsd_simpleType,
        })

    def _xsd_sequence(self, attrs, parent_element,
                      schema_path, all_schemata):
        new_element = dumco.schema.sequence.Sequence(
            attrs, all_schemata[schema_path])
        particle = dumco.schema.uses.Particle(attrs, new_element, self)
        parent_element.children.append(particle)

        return ((new_element, particle), {
            'any': XsdElementFactory._xsd_any,
            'annotation': XsdElementFactory._noop_handler,
            'choice': XsdElementFactory._xsd_choice,
            'element': XsdElementFactory._xsd_element,
            'group': XsdElementFactory._xsd_group,
            'sequence': XsdElementFactory._xsd_sequence,
        })

    def _xsd_simpleContent(self, attrs, parent_element,
                           schema_path, all_schemata):
        new_element = dumco.schema.prv.simple_content.SimpleContent(
            attrs, all_schemata[schema_path])
        parent_element.children.append(new_element)

        return (new_element, {
            'annotation': XsdElementFactory._noop_handler,
            'extension': XsdElementFactory._xsd_extension_in_simpleContent,
            'restriction': XsdElementFactory._xsd_restriction_in_simpleContent,
        })

    def _xsd_simpleType(self, attrs, parent_element,
                        schema_path, all_schemata):
        new_element = dumco.schema.simple_type.SimpleType(
            attrs, all_schemata[schema_path])
        parent_element.children.append(new_element)

        _add_to_parent_schema(new_element, attrs, all_schemata[schema_path],
                              'simple_types', self, parents=self.parents,
                              is_type=True)

        return (new_element, {
            'annotation': XsdElementFactory._noop_handler,
            'list': XsdElementFactory._xsd_list,
            'restriction': XsdElementFactory._xsd_restriction,
            'union': XsdElementFactory._xsd_union,
        })

    def _xsd_union(self, attrs, parent_element,
                   schema_path, all_schemata):
        new_element = dumco.schema.prv.union.Union(
            attrs, all_schemata[schema_path])
        parent_element.children.append(new_element)

        return (new_element, {
            'annotation': XsdElementFactory._noop_handler,
            'simpleType': XsdElementFactory._xsd_simpleType,
        })
