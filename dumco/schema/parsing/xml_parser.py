# Distributed under the GPLv2 License; see accompanying file COPYING.

from __future__ import print_function

import collections
import os.path
import xml.dom.minidom
import xml.sax
import xml.sax.handler

from dumco.utils.file_utils import enumerate_files


class _XmlContentHandler(xml.sax.handler.ContentHandler):
    NamespacePair = collections.namedtuple('NamespacePair', ['prefix', 'uri'])

    def __init__(self, document_path, documents, element_factory):
        xml.sax.handler.ContentHandler.__init__(self)

        self.document_path = document_path
        self.documents = documents
        self.element_factory = element_factory
        # Using this stack we undefine namespaces in the reversed
        # order of their definition.
        self.namespace_stack = []

    def startPrefixMapping(self, prefix, uri):
        self.namespace_stack.append(
            _XmlContentHandler.NamespacePair(prefix, uri))

        self.element_factory.define_namespace(prefix, uri)

    def endPrefixMapping(self, prefix):
        uri = None

        removed = False
        for i in xrange(len(self.namespace_stack) - 1, -1, -1):
            if prefix != self.namespace_stack[i].prefix:
                continue

            if not removed:
                del self.namespace_stack[i]
                removed = True
            else:
                uri = self.namespace_stack[i].uri
                break

        self.element_factory.define_namespace(prefix, uri)

    def startElementNS(self, name, qname, attrs):
        self.element_factory.new_element(
            name, attrs, self.document_path, self.documents)

    def endElementNS(self, name, qname):
        self.element_factory.finalize_current_element(name)

    def endDocument(self):
        self.element_factory.end_document()

    def characters(self, content):
        self.element_factory.current_element_append_text(content)


class XmlLoader(object):
    def __init__(self, element_factory):
        self.element_factory = element_factory

    def load_xml(self, xml_path, dir_depth):
        print('Loading XML files from {}...'.format(
            os.path.realpath(xml_path)))

        documents = {os.path.realpath(filepath): None
            for filepath in enumerate_files(
                xml_path, self.element_factory.extension, max_depth=dir_depth)}

        while any(map(lambda s: s is None, documents.itervalues())):
            for (filepath, document) in documents.items():
                if document is not None:
                    continue

                XmlLoader._load_document(filepath, filepath, documents,
                                         self.element_factory)

        return self.element_factory.finalize_documents(documents)

    @staticmethod
    def _load_document(filepath, path_or_stream, documents, element_factory):
        try:
            parser = xml.sax.make_parser()
            parser.setFeature(xml.sax.handler.feature_namespaces, 1)

            handler = _XmlContentHandler(filepath, documents, element_factory)
            parser.setContentHandler(handler)

            parser.parse(path_or_stream)
        except ParseRestart as e:
            XmlLoader._load_document(filepath, e.stream,
                                     documents, element_factory)


class ParseRestart(BaseException):
    def __init__(self, stream):
        self.stream = stream


class IncludeLogic(object):
    def __init__(self, root_path, element_factory):
        self.root_path = root_path
        self.element_factory = element_factory
        self.element_factory_included_paths = \
            element_factory.included_schema_paths.setdefault(root_path, set())

    def _is_root_node(self, node): # pragma: no cover
        return False

    def _is_include_node(self, node): # pragma: no cover
        return False

    def _get_included_path(self, node, curr_path): # pragma: no cover
        return None

    def _copy_included(self, including_dom, include_node,
                       included_root, included_path): # pragma: no cover
        assert False

    def include_xml(self, curr_path):
        orig_dom = xml.dom.minidom.parse(curr_path)
        orig_root = orig_dom.documentElement

        assert self._is_root_node(orig_root), 'Root element is not recognized'

        for node in list(orig_root.childNodes):
            if not self._is_include_node(node):
                continue

            node_path = self._get_included_path(node, curr_path)
            if node_path is None:
                continue

            assert os.path.isfile(node_path), \
                'File {} does not exist'.format(node_path)

            if (node_path in self.element_factory.included_schema_paths or
                node_path in self.element_factory_included_paths):
                orig_root.removeChild(node)
                continue
            self.element_factory_included_paths.add(node_path)

            new_dom = self.include_xml(node_path)
            new_root = new_dom.documentElement

            # Copy namespace declarations.
            for i in xrange(0, new_root.attributes.length):
                a = new_root.attributes.item(i)
                if not a.name.startswith('xmlns'):
                    continue

                orig_a = orig_root.getAttribute(a.name)
                assert (orig_a == '' or orig_a == a.value), \
                    '{} in included and including document are {} and ' \
                    '{} correspondingly'.format(a.name, a.value, orig_a)

                orig_root.setAttribute(a.name, a.value)

            # Copy components from included to including.
            self._copy_included(orig_dom, node, new_root, node_path)

        return orig_dom
