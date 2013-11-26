# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import function_once

import base


_NATIVE_RNG_TYPE_NAMES = [
    'string',
    'token',
]


@function_once
def rng_builtin_types():
    return {x: base.NativeType('', x) for x in _NATIVE_RNG_TYPE_NAMES}
