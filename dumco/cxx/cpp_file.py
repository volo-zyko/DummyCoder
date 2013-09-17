# Distributed under the GPLv2 License; see accompanying file COPYING.

import itertools

import dumco.utils.source_file


nl = dumco.utils.source_file.nl
nl2 = dumco.utils.source_file.nl2
idt = dumco.utils.source_file.idt
uidt = dumco.utils.source_file.uidt
nl_idt = dumco.utils.source_file.nl_idt
nl_idt2 = dumco.utils.source_file.nl_idt2
nl_uidt = dumco.utils.source_file.nl_uidt
nl_uidt2 = dumco.utils.source_file.nl_uidt2
nl2_uidt = dumco.utils.source_file.nl2_uidt
nl2_uidt2 = dumco.utils.source_file.nl2_uidt2
valid = dumco.utils.source_file.valid
ValidatingSourceWrapper = dumco.utils.source_file.ValidatingSourceWrapper
FileGuard = dumco.utils.source_file.FileGuard


class CppSourceFile(dumco.utils.source_file.SourceFile):
    def __init__(self, filename, append=False):
        super(CppSourceFile, self).__init__(filename, append)

        self.namespaces = []

    def done(self):
        assert not self.namespaces

        super(CppSourceFile, self).done()

    def add_include(self, filename, system=False, last=False):
        self << '#include ' << ('<' if system else '"')
        self << filename << ('>' if system else '"')
        self << (nl2 if last else nl)

    def _open_namespaces(self, namespaces):
        for ns in namespaces:
            self << 'namespace' << ('' if ns is '' else ' ' + ns)
            self << nl << '{' << nl
        if namespaces:
            self << nl

        self.namespaces.extend(namespaces)

    def _close_namespaces(self, namespaces=None):
        if namespaces is None:
            namespaces = self.namespaces
            del self.namespaces[0:]
        elif namespaces:
            assert len(self.namespaces) >= len(namespaces)
            del self.namespaces[-len(namespaces):]

        if namespaces:
            self << nl
        for ns in reversed(namespaces):
            self << '} // ' << ('anon namespace' if ns == ''
                                else 'namespace {}'.format(ns)) << nl


class CppHeaderFile(CppSourceFile):
    def __init__(self, filename, append=False):
        super(CppHeaderFile, self).__init__(filename, append)

        assert filename.endswith('.h'), \
            'This class is intended only for header files'

        self << '#pragma once' << nl2


class NsGuard(object):
    def __init__(self, source, namespaces):
        self.source = source

        diff = list(itertools.dropwhile(lambda x: x[0] == [1],
            itertools.izip_longest(namespaces, source.namespaces,
                                   fillvalue=None)))

        self.closed_nss = reduce(
            lambda acc, x: acc if x[1] is None else (acc + [x[1]]), diff, [])
        self.added_nss = reduce(
            lambda acc, x: acc if x[0] is None else (acc + [x[0]]), diff, [])

    def __enter__(self):
        self.source._close_namespaces(self.closed_nss)
        self.source._open_namespaces(self.added_nss)

    def __exit__(self, exc_type, exc_value, traceback):
        self.source._close_namespaces(self.added_nss)
        self.source._open_namespaces(self.closed_nss)
