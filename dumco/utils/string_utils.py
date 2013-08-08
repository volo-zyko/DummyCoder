# Distributed under the GPLv2 License; see accompanying file COPYING.


upper_first_letter = lambda name: name[:1].upper() + name[1:]

cxx_namespaces = lambda namespaces: '{0}::'.format('::'.join(namespaces))
