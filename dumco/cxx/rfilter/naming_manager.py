# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.string_utils import *


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
            return name_formatter(self, ct)
        return '{}{}'.format(cxx_namespaces(nss), name_formatter(self, ct))

    def consumer_class(self, ct):
        return '{}_AbstractConsumer'.format(cxx_norm_name(ct.name))

    def consumer_class_ns(self, ct, current_nss):
        return self._class_ns(ct, current_nss, NamingManager.consumer_class)

    def state_class(self, ct):
        return '{}_State'.format(cxx_norm_name(ct.name))

    def state_class_ns(self, ct, current_nss):
        return self._class_ns(ct, current_nss, NamingManager.state_class)

    def set_attribute(self, ct, attribute):
        return 'Set_{}_Attribute'.format(cxx_name(ct, attribute))

    def get_consumer(self, ct, element):
        return 'Get_{}_Consumer'.format(cxx_name(ct, element))

    def set_present(self, ct, element):
        return 'Set_{}_Present'.format(cxx_name(ct, element))

    def set_leaf(self, ct, element):
        return 'Set_{}_Leaf'.format(cxx_name(ct, element))
