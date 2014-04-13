# Distributed under the GPLv2 License; see accompanying file COPYING.

import collections
import sys

import checks


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

    def __setattr__(self, name, value):
        if name not in self.__dict__:
            tb = sys._current_frames().values()[0]
            assert (tb.f_back.f_code.co_name == '__init__' or
                    tb.f_back.f_code.co_filename.endswith('decorators.py')), \
                'Setting non-existent attribute'
        self.__dict__[name] = value


# Utility class necessary for better traversing dumco model.
ChildComponent = collections.namedtuple('ChildComponent',
                                        ['parent', 'component'])


class Compositor(SchemaBase):
    def __init__(self, parent_schema):
        super(Compositor, self).__init__(parent_schema)

        self.members = []

    def traverse_with_parents(self, flatten=True):
        for x in self.members:
            assert ((checks.is_particle(x) and
                     (checks.is_terminal(x.term) or
                      checks.is_compositor(x.term)))
                    or
                    (checks.is_attribute_use(x) and
                     (checks.is_attribute(x.attribute) or
                      checks.is_any(x.attribute)))
                    or
                    checks.is_text(x)), \
                'Unknown member in compositor'

            if (checks.is_particle(x) and
                    checks.is_compositor(x.term) and flatten):
                for pair in x.term.traverse_with_parents(flatten=flatten):
                    yield pair
            else:
                yield ChildComponent(self, x)


class DataComponent(SchemaBase):
    # Element of attribute.
    def __init__(self, name, parent_schema):
        super(DataComponent, self).__init__(parent_schema)

        self.name = name
        self.type = None


class NativeType(SchemaBase):
    # Represents native (predefined) named type in certain namespace/uri.
    def __init__(self, uri, name):
        super(NativeType, self).__init__(None)

        self.uri = uri
        self.name = name


# Value constraint helps maintaining default/fixed values.
# If 'fixed' is true then 'value' contains fixed value; if 'fixed' is false
# then 'value' contains default value. If there are no constraints then
# 'value' = None.
ValueConstraint = collections.namedtuple('ValueConstraint',
                                         ['fixed', 'value'])
