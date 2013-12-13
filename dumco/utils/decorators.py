# Distributed under the GPLv2 License; see accompanying file COPYING.

import collections
from functools import partial


def function_once(func):
    OptionalValue = collections.namedtuple(
        'OptionalValue', ['defined', 'value'])

    def decorated(*args, **kwargs):
        if not decorated.run.defined:
            decorated.run = OptionalValue(True, func(*args, **kwargs))
        return decorated.run.value

    decorated.run = OptionalValue(False, None)
    return decorated


class method_once(object):
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func
        return partial(self, obj)

    def __call__(self, obj, *args, **kwargs):
        if not hasattr(obj, '_cache'):
            obj._cache = {}
        cache = obj._cache

        key = hash((obj, self.func))
        if key not in cache:
            cache[key] = self.func(obj, *args, **kwargs)

        return cache[key]
