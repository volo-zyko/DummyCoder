# Distributed under the GPLv2 License; see accompanying file COPYING.

import rng_base


def rng_param(attrs, parent_element, factory, schema_path, all_schemata):
    param = RngParam(attrs, parent_element, schema_path, factory)
    parent_element.children.append(param)

    return (param, {})


class RngParam(rng_base.RngBase):
    def __init__(self, attrs, parent_element, schema_path, factory):
        super(RngParam, self).__init__(attrs, parent_element)

        self.name = factory.get_attribute(attrs,  'name')

    def append_text(self, text):
        self.text += text

    def _dump_internals(self, fhandle, indent): # pragma: no cover
        fhandle.write(' name="{}"'.format(self.name))
        return super(RngParam, self)._dump_internals(fhandle, indent)
