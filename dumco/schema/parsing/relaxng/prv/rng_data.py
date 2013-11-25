# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_param


def rng_data(attrs, parent_element, factory, schema_path, all_schemata):
    return (parent_element, {
        'param': rng_param.rng_param,
    })
