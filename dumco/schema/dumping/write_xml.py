# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.base as base
import dumco.utils.string_utils


XSD_PREFIX = 'xsd'
XML_PREFIX = 'xml'


class XmlWriter(object):
    _EMPTY_CONTENT = 0
    _SIMPLE_CONTENT = 1
    _COMPLEX_CONTENT = 2

    def __init__(self):
        self.indentation = 0
        self.namespaces = {}
        self.contents = []
        self.is_parent_finalized = True
        self.parent_stack = []

        self._write('<?xml version="1.0" encoding="UTF-8"?>\n')

    def done(self):
        assert len(self.contents) == 0
        assert len(self.parent_stack) == 0
        self._close()

    def open_tag(self, prefix, uri, tag):
        self._finalize_parent_open_tag(XmlWriter._COMPLEX_CONTENT)
        self.contents.append(XmlWriter._EMPTY_CONTENT)
        self.parent_stack.append('{}:{}'.format(uri, tag))

        self._indent()
        if prefix == '':
            self._write('<{}'.format(tag))
        else:
            self._write('<{}:{}'.format(prefix, tag))
        self.define_namespace(prefix, uri)
        self.is_parent_finalized = False

        self.indentation += 1

    def close_tag(self, prefix, uri, tag):
        self.indentation -= 1

        self.is_parent_finalized = True
        if self.contents[-1] == XmlWriter._EMPTY_CONTENT:
            self._write('/>\n')
        else:
            if self.contents[-1] == XmlWriter._COMPLEX_CONTENT:
                self._indent()

            if prefix == '':
                self._write('</{}>'.format(tag))
            else:
                self._write('</{}:{}>\n'.format(prefix, tag))

        self.parent_stack.pop()
        self.contents.pop()

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

    def add_text(self, text):
        self._finalize_parent_open_tag(XmlWriter._SIMPLE_CONTENT, False)
        self._write(text)

    def add_comment(self, comment):
        self.open_comment(comment)
        self.close_comment(True)

    def open_comment(self, text=None):
        self._finalize_parent_open_tag(XmlWriter._COMPLEX_CONTENT)
        self._indent()
        if text is None:
            self._write('<!--\n')
            self.indentation += 1
        else:
            self._write('<!-- {}'.format(text))

    def close_comment(self, one_liner=False):
        if one_liner:
            self._write(' -->\n')
        else:
            self.indentation -= 1
            self._indent()
            self._write('-->\n')

    def _finalize_parent_open_tag(self, parent_content, with_new_line=True):
        if not self.is_parent_finalized:
            if with_new_line:
                self._write('>\n')
            else:
                self._write('>')
            self.contents[-1] = parent_content
            self.is_parent_finalized = True

    def _indent(self):
        self._write(' ' * self.indentation * 2)

    def _write(self, _):
        assert False, '_write() should be overridden'

    def _close(self):
        assert False, '_close() should be overridden'


class TagGuard(object):
    def __init__(self, writer, tag, uri, prefix=None):
        self.tag = tag
        self.uri = uri
        self.prefix = prefix
        self.writer = writer

    def __enter__(self):
        self.writer.open_tag(self.prefix, self.uri, self.tag)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.writer.close_tag(self.prefix, self.uri, self.tag)
        return exc_value is None


class CommentGuard(object):
    def __init__(self, writer):
        self.writer = writer

    def __enter__(self):
        self.writer.open_comment()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.writer.close_comment()
        return exc_value is None


def get_qname(name, own_schema, other_schema, context):
    if own_schema != other_schema:
        if own_schema is not None:
            context.store_import_namespace(own_schema.prefix,
                                           own_schema.target_ns)
        return '{}:{}'.format(own_schema.prefix, name)
    return name
