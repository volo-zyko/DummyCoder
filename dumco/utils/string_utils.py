# Distributed under the GPLv2 License; see accompanying file COPYING.

import string
import xml.sax.saxutils

import dumco.schema.checks


def cxx_name(ct, member):
    if ct.schema == member.schema:
        return cxx_norm_name(member.name)
    elif dumco.schema.checks.is_xml_attribute(member):
        return 'xml_{}'.format(cxx_norm_name(member.name))
    else:
        return '{}_{}'.format(cxx_norm_name(member.schema.prefix),
                              cxx_norm_name(member.name))


cxx_namespaces = lambda namespaces: '{}::'.format(
    '::'.join([cxx_norm_name(n) for n in namespaces]))


def cxx_norm_name(name):
    res = []
    for c in name:
        if c in string.ascii_letters or c in string.digits or c == '_':
            res.append(c)
        elif (c == '-'):
            res.append('__')
        else:
            res.append('_{:02x}_'.format(c))
    return ''.join('_' + res if not res or res[0] in string.digits else res)


_ENTITIES = {chr(x): '&#{};'.format(x) for x in xrange(127, 256)}
def quote_xml_string(value):
    return xml.sax.saxutils.quoteattr(str(value), _ENTITIES)


upper_first_letter = lambda name: name[:1].upper() + name[1:]
