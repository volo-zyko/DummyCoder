# Distributed under the GPLv2 License; see accompanying file COPYING.

from __future__ import print_function

import os.path
import xml.sax

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
        self.element_factory.finalize_current_element()

    def characters(self, content):
        self.element_factory.current_element_append_text(content)


class XmlLoader(object):
    def __init__(self, element_factory):
        self.element_factory = element_factory

    def load_xml(self, xml_path):
        print('Loading XML files from {0}...'.format(
            os.path.realpath(xml_path)))

        documents = {os.path.realpath(filepath): None
                     for filepath in enumerate_files(
                        xml_path, self.element_factory.extension)}

        while any(map(lambda s: s is None, documents.itervalues())):
            for (filepath, document) in documents.items():
                if document is not None:
                    continue

                XmlLoader._load_document(filepath, documents,
                                         self.element_factory)

        return self.element_factory.finalize_documents(documents)

    @staticmethod
    def _load_document(filepath, documents, element_factory):
        parser = xml.sax.make_parser()
        parser.setFeature(xml.sax.handler.feature_namespaces, 1)

        handler = _XmlContentHandler(filepath, documents,
                                     element_factory)
        parser.setContentHandler(handler)

        with open(filepath, 'r') as fl:
            parser.parse(fl)
