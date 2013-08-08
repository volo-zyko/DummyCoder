# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.utils.string_utils

class NamingManager(object):
    def __init__(self, ns_converter):
        self.ns_converter = ns_converter

        self.schema_namespaces = {}

    def _class_ns(self, ct, current_nss, name_formatter):
        if ct.schema.target_ns not in self.schema_namespaces:
            self.schema_namespaces[ct.schema.target_ns] = \
                self.ns_converter.uri_to_namespaces(ct.schema.target_ns)
        nss = self.schema_namespaces[ct.schema.target_ns]

        if nss == current_nss:
            return name_formatter(ct)
        return '{0}{1}'.format(dumco.utils.string_utils.cxx_namespaces(nss),
                               name_formatter(ct))

    def consumer_class(self, ct):
        return '{0}_AbstractConsumer'.format(ct.name)

    def consumer_class_ns(self, ct, current_nss):
        return self._class_ns(ct, current_nss, consumer_class)
