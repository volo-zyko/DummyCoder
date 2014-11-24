# Distributed under the GPLv2 License; see accompanying file COPYING.

import base


def xsd_enumeration(attrs, parent_element, factory, schema_path, all_schemata):
    new_element = XsdEnumeration(attrs)
    parent_element.children.append(new_element)

    return (new_element, {
        'annotation': factory.xsd_annotation,
    })


class XsdEnumeration(base.XsdBase):
    def __init__(self, attrs):
        super(XsdEnumeration, self).__init__(attrs)

        # It's a fake object just to store the doc string associated with enum.
        self.schema_element = _XsdEnumerationDoc()
        self.value = self.attr('value')


class _XsdEnumerationDoc(object):
    def __init__(self):
        self.doc = []

    def append_doc(self, doc):
        d = doc.strip()
        if d != '':
            self.doc.append(d)
