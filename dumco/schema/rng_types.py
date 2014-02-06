# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import function_once

import base


# Constants.
RNG_NAMESPACE = 'http://relaxng.org/ns/structure/1.0'

_NATIVE_RNG_TYPE_NAMES = [
    'string',
    'token',
]


@function_once
def rng_builtin_types():
    return {x: base.NativeType(RNG_NAMESPACE, x)
            for x in _NATIVE_RNG_TYPE_NAMES}
