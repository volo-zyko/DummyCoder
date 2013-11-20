# Distributed under the GPLv2 License; see accompanying file COPYING.

import collections


def function_once(func):
    _OptionalValue = collections.namedtuple(
        '_OptionalValue', ['defined', 'value'])

    def decorated(*args, **kwargs):
        if not decorated.run.defined:
            decorated.run = _OptionalValue(True, func(*args, **kwargs))
        return decorated.run.value

    decorated.run = _OptionalValue(False, None)
    return decorated


def method_once(func):
    def decorated(self, *args, **kwargs):
        method_name = '{}.0x{:x}.0x{:x}'.format(
            self.__module__, id(self), id(func))

        if method_name not in decorated.run_map:
            decorated.run_map[method_name] = func(self, *args, **kwargs)
        return decorated.run_map[method_name]

    decorated.run_map = {}
    return decorated
