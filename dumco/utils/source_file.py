# Distributed under the GPLv2 License; see accompanying file COPYING.

import atexit
import cPickle
import os
import os.path
import stat
import string
import time
import zlib


nl = lambda sf: '{}{}'.format(sf._nl1(), sf._make_indentation())
nl2 = lambda sf: '{}{}'.format(sf._nl2(), sf._make_indentation())
idt = lambda sf: sf._indent()
uidt = lambda sf: sf._unindent()
nl_idt = lambda sf: '{}{}{}'.format(sf._nl1(), sf._indent(),
                                    sf._make_indentation())
nl_idt2 = lambda sf: '{}{}{}{}'.format(sf._nl1(), sf._indent(),
                                       sf._indent(),
                                       sf._make_indentation())
nl_uidt = lambda sf: '{}{}{}'.format(sf._nl1(), sf._unindent(),
                                     sf._make_indentation())
nl_uidt2 = lambda sf: '{}{}{}{}'.format(sf._nl1(), sf._unindent(),
                                        sf._unindent(),
                                        sf._make_indentation())
nl2_uidt = lambda sf: '{}{}{}'.format(sf._nl2(), sf._unindent(),
                                      sf._make_indentation())
nl2_uidt2 = lambda sf: '{}{}{}{}'.format(sf._nl2(), sf._unindent(),
                                         sf._unindent(),
                                         sf._make_indentation())
valid = lambda sf: ''


class SourceFile(object):
    source_hashes_pickle_path = None
    previous_files_info = {}
    current_files_info = {}

    def __init__(self, filename, append=False,
                 read_only=True, spaces_per_tab=4):
        self.filename = os.path.realpath(filename)
        self.read_only = read_only
        self.spaces_per_tab = spaces_per_tab

        self.strings = []
        self.indentation = 0
        self.nls = 0

        if SourceFile.source_hashes_pickle_path is None:
            SourceFile.source_hashes_pickle_path = os.path.join(
                os.path.dirname(self.filename), 'source_hashes.pickle')
            # Load old hash codes.
            if os.path.exists(SourceFile.source_hashes_pickle_path):
                with open(SourceFile.source_hashes_pickle_path, 'rb') as fl:
                    SourceFile.previous_files_info.update(cPickle.load(fl))

        if self.is_new_file():
            if self.read_only:
                self << '// This file is generated. DO NOT EDIT IT!' << nl
            self << '// Distributed under the GPLv2 License; see accompanying file COPYING.' << nl2
        elif not append:
            raise FileExists(self.filename)

    @staticmethod
    @atexit.register
    def save_source_hashes():
        if SourceFile.source_hashes_pickle_path:
            with open(SourceFile.source_hashes_pickle_path, 'wb') as fl:
                cPickle.dump(SourceFile.current_files_info, fl)

    def is_new_file(self):
        return (os.path.basename(self.filename) not in
                SourceFile.current_files_info)

    def done(self):
        content = ''.join(self.strings)
        basename = os.path.basename(self.filename)
        prev_file_info = (SourceFile.previous_files_info[basename] if
            basename in SourceFile.previous_files_info else (None, None))

        is_new_file = self.is_new_file()

        if is_new_file:
            content_crc = zlib.crc32(content) & 0xffffffff
        else:
            # Appending to existing file.
            content_crc = SourceFile.current_files_info[basename][0]
            content_crc = zlib.crc32(content, content_crc) & 0xffffffff

        is_same_content = prev_file_info[0] == content_crc

        if is_same_content:
            file_time = prev_file_info[1]
        else:
            file_time = time.time()
        SourceFile.current_files_info[basename] = (content_crc, file_time)

        write_mode = 'a'
        if os.path.exists(self.filename):
            if is_new_file:
                if is_same_content:
                    return # Nothing to do.
                write_mode = 'w'
            os.chmod(self.filename, stat.S_IWRITE)
        elif not os.path.exists(os.path.dirname(self.filename)):
            os.makedirs(os.path.dirname(self.filename))

        # Commit change.
        with open(self.filename, write_mode) as fl:
            fl.write(content)

        if self.read_only:
            os.chmod(self.filename, stat.S_IREAD)

        if is_same_content:
            os.utime(self.filename, (file_time, file_time))

        assert self.indentation == 0, \
            'Broken indentation in {}'.format(self.filename)

    def __lshift__(self, obj):
        if hasattr(obj, '__call__'):
            self.strings.append(obj(self))
        else:
            self.nls = 0
            self.strings.append(str(obj))
        return self

    def _nl1(self):
        if self.nls < 2:
            self.nls += 1
            return '\n'
        return ''

    def _nl2(self):
        current_nls = self.nls
        self.nls = 2
        if current_nls == 0:
            return '\n\n'
        elif current_nls == 1:
            return '\n'
        return ''

    def _indent(self):
        self.indentation += 1
        return ''

    def _unindent(self):
        assert self.indentation != 0, \
            'Cannot unindent in {}'.format(self.filename)
        self.indentation -= 1
        return ''

    def _make_indentation(self):
        return ' ' * (self.indentation * self.spaces_per_tab)


class ValidatingSourceWrapper(object):
    """Adds code to Source object only after receiving of 'valid' token"""
    def __init__(self, source):
        self.source = source
        self.pending = []

    def __lshift__(self, obj):
        if self.pending is None:
            self.source << obj
        elif obj == valid:
            for o in self.pending:
                self.source << o
            self.pending = None
        else:
            self.pending.append(obj)
        return self


class FileGuard(object):
    """Makes sure that done() is called on Source object"""
    def __init__(self, source):
        self.source = source

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        self.source.done()


class FileExists(BaseException):
    pass
