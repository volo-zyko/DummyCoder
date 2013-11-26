# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_anyName
import rng_base
import rng_choice
import rng_name
import rng_nsName


def rng_except(attrs, parent_element, factory, schema_path, all_schemata):
    excpt = RngExcept(attrs, schema_path)

    return (excpt, {
        'anyName': rng_anyName.rng_anyName,
        'choice': rng_choice.rng_choice,
        'name': rng_name.rng_name,
        'nsName': rng_nsName.rng_nsName,
    })


class RngExcept(rng_base.RngBase):
    def __init__(self, attrs, schema_path):
        super(RngExcept, self).__init__(attrs)
