# Distributed under the GPLv2 License; see accompanying file COPYING.

import os.path

import dumco.cxx.base_gendriver

import consumer
import naming_manager
import state_cpp
import state_h


class RFilterGenerationDriver(dumco.cxx.base_gendriver.GenerationDriver):
    def __init__(self, schemata, ns_converter, opacity_manager,
                 output_path, context_class, context_class_header):
        super(RFilterGenerationDriver, self).__init__(
            schemata, ns_converter, opacity_manager)

        self.context_class = context_class
        self.context_class_header = context_class_header
        self.nm = naming_manager.NamingManager(ns_converter)
        self.lm = _LocationManager(output_path, ns_converter, self.nm)
        self.namespaces = {}

    def _generate_for_complex_type(self, ct):
        self.namespaces[ct.schema.target_ns] = \
            self.nsc.uri_to_namespaces(ct.schema.target_ns)

        consumer_coder = consumer.ConsumerCoder(
            self, ct, self.context_class, self.context_class_header)
        state_h_coder = state_h.StateHeaderCoder(self, ct)
        state_cpp_coder = state_cpp.StateCppCoder(self, ct)

        consumer_coder.generate_code()
        state_h_coder.generate_code()
        state_cpp_coder.generate_code()


class _LocationManager(object):
    def __init__(self, output_path, ns_converter, naming):
        self.output_path =  output_path
        self.ns_converter = ns_converter
        self.naming = naming

        self.file_prefices = {}

    def _schema_file_prefix(self, schema):
        if schema.target_ns not in self.file_prefices:
            namespaces = self.ns_converter.uri_to_namespaces(schema.target_ns)

            self.file_prefices[schema.target_ns] = '_'.join(namespaces[1:])

        return self.file_prefices[schema.target_ns]

    def _consumer_header_name(self, ct):
        return '{}_{}.h'.format(self._schema_file_prefix(ct.schema),
                                self.naming.consumer_class(ct))

    def consumer_header_path(self, ct):
        return os.path.join(self.output_path, self._consumer_header_name(ct))

    def consumer_include_path(self, ct):
        return self._consumer_header_name(ct)

    def _state_header_name(self, ct):
        return '{}_{}.h'.format(self._schema_file_prefix(ct.schema),
                                self.naming.state_class(ct))

    def state_header_path(self, ct):
        return os.path.join(self.output_path, self._state_header_name(ct))

    def state_include_path(self, ct):
        return self._state_header_name(ct)

    def state_source_path(self, ct):
        state_file = '{}_{}.cpp'.format(self._schema_file_prefix(ct.schema),
                                        self.naming.state_class(ct))
        return os.path.join(self.output_path, state_file)
