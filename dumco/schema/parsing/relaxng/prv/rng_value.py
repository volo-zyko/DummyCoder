# Distributed under the GPLv2 License; see accompanying file COPYING.


def rng_value(attrs, parent_element, factory, schema_path, all_schemata):
    return (parent_element, {
        'vdata': factory.noop_handler,
    })
