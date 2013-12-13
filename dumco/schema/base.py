# Distributed under the GPLv2 License; see accompanying file COPYING.

import collections
import sys

from dumco.utils.decorators import function_once


# Constants.
XML_NAMESPACE = 'http://www.w3.org/XML/1998/namespace'

UNBOUNDED = sys.maxsize


@function_once
def xml_attributes():
    attrs = {x: XmlAttribute(x) for x in ['base', 'id', 'lang', 'space']}
    attrs['space'].constraint = ValueConstraint(None, 'preserve')
    return attrs


class SchemaBase(object):
    def __init__(self, parent_schema):
        self.schema = parent_schema
        self._docs = []

    def append_doc(self, doc):
        d = doc.strip()
        if d != '':
            self._docs.append(d)

    @property
    def doc(self):
        return ' '.join(self._docs)

    def __setattr__(self, name, value):
        if name not in self.__dict__:
            tb = sys._current_frames().values()[0]
            assert (tb.f_back.f_code.co_name == '__init__' or
                    tb.f_back.f_code.co_filename.endswith('decorators.py')), \
                'Setting non-existent attribute'
        self.__dict__[name] = value


class NativeType(SchemaBase):
    def __init__(self, uri, name):
        super(NativeType, self).__init__(None)

        self.uri = uri
        self.name = name


class SchemaText(SchemaBase):
    def __init__(self, simple_type):
        super(SchemaText, self).__init__(None)

        self.name = 'text()'
        self.type = simple_type


ValueConstraint = collections.namedtuple('ValueConstraint',
                                         ['fixed', 'value'])


class XmlAttribute(SchemaBase):
    def __init__(self, name):
        super(XmlAttribute, self).__init__(None)

        self.name = name
        self.constraint = ValueConstraint(False, None)
