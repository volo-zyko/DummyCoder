# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.elements

import rng_base
import rng_define
import rng_start


def rng_grammar(attrs, parent_element, factory, schema_path, all_schemata):
    grammar = RngGrammar(attrs, schema_path, factory)
    all_schemata[schema_path] = grammar

    return (grammar, {
        'define': rng_define.rng_define,
        # 'div': factory.noop_handler,
        # 'include': factory.noop_handler,
        'start': rng_start.rng_start,
    })


class RngGrammar(rng_base.RngBase):
    def __init__(self, attrs, schema_path, factory):
        super(RngGrammar, self).__init__(attrs)

        self.schemata = []
        for (uri, prefix) in factory.all_namespace_prefices.iteritems():
            schema = dumco.schema.elements.Schema(uri)
            schema.set_prefix(factory.all_namespace_prefices)
            schema.filename = schema.prefix

            self.schemata.append(schema)
