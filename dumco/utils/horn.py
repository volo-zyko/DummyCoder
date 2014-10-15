# Distributed under the GPLv2 License; see accompanying file COPYING.

from __future__ import print_function

import sys


class Horn(object):
    _verbosity = None

    def set_verbosity(self, verbosity):
        if Horn._verbosity is None:
            Horn._verbosity = verbosity

    def peep(self, format, *args):
        if self._verbosity >= 2:
            print(format.format(*[str(a) for a in args]), file=sys.stdout)

    def beep(self, format, *args):
        if self._verbosity >= 1:
            print(format.format(*[str(a) for a in args]), file=sys.stdout)

    def honk(self, format, *args):
        print(format.format(*[str(a) for a in args]), file=sys.stderr)


horn = Horn()
