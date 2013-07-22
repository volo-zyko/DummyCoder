# Distributed under the GPLv2 License; see accompanying file COPYING.


def function_once(func): # pragma: no cover
    def decorated(*args, **kwargs):
        if not decorated.run[0]:
            decorated.run = (True, func(*args, **kwargs))
        return decorated.run[1]

    decorated.run = (False, None)
    return decorated


def method_once(func):
    def decorated(self, *args, **kwargs):
        method_name = '{0}.0x{1:x}.0x{2:x}'.format(
            self.__module__, id(self), id(func))

        if method_name not in decorated.run_map:
            decorated.run_map[method_name] = func(self, *args, **kwargs)
        return decorated.run_map[method_name]

    decorated.run_map = {}
    return decorated
