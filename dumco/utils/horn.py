# Distributed under the GPLv2 License; see accompanying file COPYING.

from __future__ import print_function

import sys


class Horn(object):
    _verbosity = None

    def set_verbosity(self, verbosity):
        if Horn._verbosity is None:
            Horn._verbosity = verbosity

    def peep(self, form, *args):
        if self._verbosity >= 2:
            print(form.format(*args), file=sys.stdout)

    def beep(self, form, *args):
        if self._verbosity >= 1:
            print(form.format(*args), file=sys.stdout)

    def howl(self, form, *args):
        print('WARNING: ' + form.format(*args), file=sys.stderr)

    def honk(self, form, *args):
        print('ERROR: ' + form.format(*args), file=sys.stderr)


horn = Horn()
