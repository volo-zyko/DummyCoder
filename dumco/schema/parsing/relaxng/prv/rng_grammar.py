# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.elements

import dumco.schema.parsing.relaxng.element_factory

import rng_base
import rng_define
import rng_start


def rng_grammar(attrs, parent_element, factory, schema_path, all_schemata):
    grammar = RngGrammar(attrs, parent_element, schema_path, factory)
    all_schemata[schema_path] = grammar

    return (grammar, {
        'define': rng_define.rng_define,
        'div': factory.rng_div,
        # 'include': factory.noop_handler,
        'start': rng_start.rng_start,
    })


class RngGrammar(rng_base.RngBase):
    def __init__(self, attrs, parent_element, schema_path, factory):
        super(RngGrammar, self).__init__(attrs, parent_element)

        self.schemata = []
        for (uri, prefix) in factory.all_namespace_prefices.iteritems():
            schema = dumco.schema.elements.Schema(uri)
            schema.set_prefix(factory.all_namespace_prefices)
            schema.filename = schema.prefix

            self.schemata.append(schema)

    def _dump_internals(self, fhandle, indent): # pragma: no cover
        fhandle.write(' xmlns="{}"'.format(
            dumco.schema.parsing.relaxng.element_factory.RNG_NAMESPACE))
        for s in self.schemata:
            fhandle.write(' xmlns:{}="{}"'.format(s.prefix, s.target_ns))
        return super(RngGrammar, self)._dump_internals(fhandle, indent)
