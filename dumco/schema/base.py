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
        d = doc.strip()
        if d != '':
            self._docs.append(d)

    @property
    def doc(self):
        return ' '.join(self._docs)

    def equal(self, other):
        return self.schema == other.schema

    def __setattr__(self, name, value):
        if name not in self.__dict__:
            tb = sys._current_frames().values()[0]
            assert (tb.f_back.f_code.co_name == '__init__' or
                    tb.f_back.f_code.co_filename.endswith('decorators.py')), \
                'Setting non-existent attribute'
        self.__dict__[name] = value


class Compositor(SchemaBase):
    def __init__(self, parent_schema):
        super(Compositor, self).__init__(parent_schema)

        self.members = []

    def equal(self, other):
        # Compositors don't have to be from the same schema.
        return (len(self.members) == len(other.members) and
                all([x.equal(y)
                     for (x, y) in zip(self.members, other.members)]))


class DataComponent(SchemaBase):
    # Element or attribute.
    def __init__(self, name, parent_schema):
        super(DataComponent, self).__init__(parent_schema)

        self.name = name
        self.type = None

    def equal(self, other):
        eq = super(DataComponent, self).equal(other)

        return (eq and self.name == other.name and
                self.type is not None and self.type.equal(other.type))


class NativeType(SchemaBase):
    # Represents native (predefined) named type in certain namespace/uri.
    def __init__(self, uri, name):
        super(NativeType, self).__init__(None)

        self.uri = uri
        self.name = name

    def equal(self, other):
        # Nothing to check in the base class.
        return (self.uri == other.uri and self.name == other.name)


# Value constraint helps maintaining default/fixed values.
# If 'fixed' is true then 'value' contains fixed value; if 'fixed' is false
# then 'value' contains default value. If there are no constraints then
# 'value' = None.
ValueConstraint = collections.namedtuple('ValueConstraint',
                                         ['fixed', 'value'])
