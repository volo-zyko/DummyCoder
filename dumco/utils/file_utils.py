# Distributed under the GPLv2 License; see accompanying file COPYING.

import os
import os.path
import stat


def enumerate_files(start_path, file_ending,
                    exclude_writable=False, max_depth=None):
    depth = 0
    for (root, dirs, files) in os.walk(start_path):
        depth = depth + 1
        if max_depth is not None and depth > max_depth:
            return

        for f in files:
            if not f.endswith(file_ending):
                continue

            filename = os.path.normpath(os.path.join(root, f))
            if stat.S_ISLNK(os.lstat(filename).st_mode):
                continue

            if exclude_writable:
                s = os.stat(filename)
                if s.st_mode & stat.S_IWRITE:
                    continue

            yield filename

