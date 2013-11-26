# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.cxx.cpp_file import *


class StateCppCoder(object):
    def __init__(self, gd, ct):
        self.gd = gd
        self.ct = ct
        self.ct_namespaces = gd.nsc.uri_to_namespaces(ct.schema.target_ns)

    def generate_code(self):
        sf = CppSourceFile(self.gd.lm.state_source_path(self.ct))
        with FileGuard(sf):
            sf.add_include(self.gd.lm.state_include_path(self.ct))
            sf.add_include(self.gd.lm.consumer_include_path(self.ct), last=True)

            with NsGuard(sf, self.ct_namespaces):
                pass
