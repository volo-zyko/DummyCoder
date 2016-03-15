# Distributed under the GPLv2 License; see accompanying file COPYING.

from __future__ import print_function

import sys


class Horn(object):
    _verbosity = None
    _suppress_warnings = False

    def set_verbosity(self, verbosity):
        if Horn._verbosity is None:
            Horn._verbosity = verbosity

    def set_suppress_warnings(self, value):
        Horn._suppress_warnings = value

    def peep(self, form, *args):
        if self._verbosity >= 2:
            print(form.format(*args), file=sys.stdout)

    def beep(self, form, *args):
        if self._verbosity >= 1:
            print(form.format(*args), file=sys.stdout)

    def howl(self, form, *args):
        if not self._suppress_warnings:
            print('WARNING: ' + form.format(*args), file=sys.stderr)

    def honk(self, form, *args):
        print('ERROR: ' + form.format(*args), file=sys.stderr)


horn = Horn()
