# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.checks


class OxmlNamer(object):
    def name(self, element, parent_name, parent_class, index):
        name = parent_name[:1].upper() + parent_name[1:]
        if dumco.schema.checks.is_complex_type(element):
            return 'CT_{0}'.format(name)
        elif dumco.schema.checks.is_simple_type(element):
            return 'ST_{0}'.format(name)
        else:
            return '{0}{1}{2}'.format(name, element.__class__.__name__,
                                      index if index is not None else '')


class Fb2Namer(object):
    def name(self, element, parent_name, parent_class, index):
        if dumco.schema.checks.is_complex_type(element):
            return '{0}{1}Ct'.format(parent_name,
                                     parent_class.__name__)
        elif dumco.schema.checks.is_simple_type(element):
            return '{0}{1}St'.format(parent_name,
                                     parent_class.__name__)
        else:
            return '{0}{1}{2}'.format(parent_name, element.__class__.__name__,
                                      index if index is not None else '')
