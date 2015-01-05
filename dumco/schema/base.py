# Distributed under the GPLv2 License; see accompanying file COPYING.

import collections
import sys


# Constants.
XML_NAMESPACE = 'http://www.w3.org/XML/1998/namespace'

UNBOUNDED = sys.maxsize


class SchemaBase(object):
    # Base class for almost all objects in dumco model.
    # Contains documentation and a reference to the containing schema.
    # Schema can be None in case of predefined schema.
    def __init__(self, parent_schema):
        self.schema = parent_schema
        self._docs = []

    def append_doc(self, doc):
        text = doc.strip()
        if text != '':
            self._docs.append(text)

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


class Compositor(SchemaBase):
    def __init__(self):
        super(Compositor, self).__init__(None)

        self.members = []


class DataComponent(SchemaBase):
    # Element or attribute.
    def __init__(self, name, default, fixed, qualified, parent_schema):
        super(DataComponent, self).__init__(parent_schema)

        self.name = name
        self.type = None
        self.qualified = qualified
        self.constraint = ValueConstraint(default, fixed)


class NativeType(SchemaBase):
    # Represents native (predefined) named type in certain namespace/uri.
    def __init__(self, parent_schema, name):
        super(NativeType, self).__init__(parent_schema)

        self.uri = parent_schema.target_ns
        self.name = name


# Value constraint helps maintaining default/fixed values.
# If 'fixed' is true then 'value' contains fixed value; if 'fixed' is false
# then 'value' contains default value. If there are no constraints then
# 'value' = None.
ValueConstraint = collections.namedtuple('ValueConstraint',
                                         ['value', 'fixed'])
