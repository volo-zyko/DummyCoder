# Distributed under the GPLv2 License; see accompanying file COPYING.

class XsdBase(object):
    def __init__(self, attrs):
        self.attrs = {x[1]: v for (x,v) in attrs.items()}
        self.children = []

    def attr(self, name):
        return self.attrs.get(name, None)
