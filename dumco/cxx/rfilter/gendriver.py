# Distributed under the GPLv2 License; see accompanying file COPYING.

import os.path

import dumco.cxx.base_gendriver

import consumer
import naming_manager


class RFilterGenerationDriver(dumco.cxx.base_gendriver.GenerationDriver):
    def __init__(self, schemata, ns_converter, opacity_manager,
                 output_path, context_class, context_class_header):
        super(RFilterGenerationDriver, self).__init__(
            schemata, ns_converter, opacity_manager)

        self.context_class = context_class
        self.context_class_header = context_class_header
        self.nm = naming_manager.NamingManager(ns_converter)
        self.lm = _LocationManager(output_path, ns_converter, self.nm)

    def _generate_for_complex_type(self, ct):
        consumer_coder = consumer.ConsumerCoder(
            self, ct, self.context_class, self.context_class_header)

        consumer_coder.generate_code()


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

    def _consumer_file_name(self, ct):
        return '{0}_{1}.h'.format(self._schema_file_prefix(ct.schema),
                                  self.naming.consumer_class(ct))

    def consumer_full_path(self, ct):
        return os.path.join(self.output_path, self._consumer_file_name(ct))

    def consumer_include_path(self, ct):
        return '{0}/{1}'.format(self.opts.packageName,
            self._consumer_file_name(ct))
