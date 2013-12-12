# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import rng_base
import rng_except
import rng_param


def rng_data(attrs, parent_element, factory, grammar_path, all_grammars):
    data = RngData(attrs, parent_element, factory)
    parent_element.children.append(data)

    return (data, {
        'param': rng_param.rng_param,
        'except': rng_except.rng_except,
    })


class RngData(rng_base.RngBase):
    def __init__(self, attrs, parent_element, factory):
        super(RngData, self).__init__(attrs, parent_element)

        self.params = []
        self.except_pattern = None
        self.datatypes_uri = factory.get_datatypes_uri()
        type_name = factory.get_attribute(attrs, 'type').strip()
        self.type = factory.builtin_types(self.datatypes_uri)[type_name]

    @method_once
    def finalize(self, grammar, all_schemata, factory):
        for c in self.children:
            assert (isinstance(c, rng_param.RngParam) or
                    isinstance(c, rng_except.RngExceptPattern)), \
                'Wrong content of data element'

            c.finalize(grammar, all_schemata, factory)
            if isinstance(c, rng_param.RngParam):
                self.params.append(c)
            elif isinstance(c, rng_except.RngExceptPattern):
                assert self.except_pattern is None, \
                    'More than one except element in data element'
                self.except_pattern = c

        super(RngData, self).finalize(grammar, all_schemata, factory)

    def _dump_internals(self, fhandle, indent):
        fhandle.write(' type="{}" datatypeLibrary="{}"'.
                      format(self.type.name, self.datatypes_uri))
        if self.params or self.except_pattern is not None:
            fhandle.write('>\n')
            for p in self.params:
                p.dump(fhandle, indent)
            if self.except_pattern is not None:
                self.except_pattern.dump(fhandle, indent)
            return rng_base.RngBase._CLOSING_TAG

        return rng_base.RngBase._CLOSING_EMPTY_TAG
