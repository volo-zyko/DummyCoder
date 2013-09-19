# Distributed under the GPLv2 License; see accompanying file COPYING.

from __future__ import print_function

import os.path
import xml.sax
import xml.sax.handler

from dumco.utils.file_utils import enumerate_files


class _XmlContentHandler(xml.sax.handler.ContentHandler):
    def __init__(self, document_path, documents, element_factory):
        xml.sax.handler.ContentHandler.__init__(self)

        self.document_path = document_path
        self.documents = documents
        self.element_factory = element_factory

    def startPrefixMapping(self, prefix, uri):
        self.element_factory.open_namespace(prefix, uri)

    def endPrefixMapping(self, prefix):
        self.element_factory.close_namespace(prefix)

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
