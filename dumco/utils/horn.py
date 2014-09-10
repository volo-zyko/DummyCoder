# Distributed under the GPLv2 License; see accompanying file COPYING.

from __future__ import print_function

import sys


class Horn(object):
    def __init__(self, verbose=True):
        self.verbose = verbose

    def beep(self, format, *args):
        if self.verbose:
            print(format.format(*[str(a) for a in args]), file=sys.stdout)

    def honk(self, format, *args):
        print(format.format(*[str(a) for a in args]), file=sys.stderr)
