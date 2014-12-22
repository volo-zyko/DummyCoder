# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import function_once

import base
import model


# Constants.
RNG_NAMESPACE = 'http://relaxng.org/ns/structure/1.0'

_NATIVE_RNG_TYPE_NAMES = [
    'string',
    'token',
]


@function_once
def rng_builtin_types():
    return {x: base.NativeType(get_rng_schema(), x)
            for x in _NATIVE_RNG_TYPE_NAMES}


@function_once
def get_rng_schema():
    return model.Schema(RNG_NAMESPACE, 'rng')
