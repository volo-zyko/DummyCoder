# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base
import rng_except


def rng_nsName(attrs, parent_element, factory, schema_path, all_schemata):
    nsName = RngNsName(attrs, schema_path)

    return (nsName, {
        'except': rng_except.rng_except,
    })


class RngNsName(rng_base.RngBase):
    def __init__(self, attrs, schema_path):
        super(RngNsName, self).__init__(attrs)
