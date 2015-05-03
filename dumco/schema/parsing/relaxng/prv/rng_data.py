# Distributed under the GPLv2 License; see accompanying file COPYING.

from dumco.utils.decorators import method_once

import base
import rng_except
import rng_param
import utils


def rng_data(attrs, parent_element, builder, grammar_path, all_grammars):
    type_name = builder.get_attribute(attrs, 'type').strip()
    datatypes_uri = builder.get_datatypes_uri()
    builtin_type = builder.builtin_types(datatypes_uri)[type_name]

    parent_element.children.append(RngData(datatypes_uri, builtin_type))

    return (parent_element.children[-1], {
        'param': rng_param.rng_param,
        'except': rng_except.rng_except,
    })


class RngData(base.RngBase):
    def __init__(self, datatypes_uri, builtin_type):
        super(RngData, self).__init__()

        self.params = []
        self.except_pattern = None
        self.datatypes_uri = datatypes_uri
        self.type = builtin_type

    @method_once
    def finalize(self, grammar, builder):
        for c in self.children:
            assert (isinstance(c, rng_param.RngParam) or
                    isinstance(c, rng_except.RngExceptPattern)), \
                'Wrong content of data element'

            c = c.finalize(grammar, builder)
            if isinstance(c, rng_param.RngParam):
                self.params.append(c)
            elif isinstance(c, rng_except.RngExceptPattern):
                assert self.except_pattern is None, \
                    'More than one except element in data element'
                if len(c.patterns) != 0:
                    self.except_pattern = c

        return super(RngData, self).finalize(grammar, builder)

    def dump(self, context):
        with utils.RngTagGuard('data', context):
            context.add_attribute('type', self.type.name)
            context.add_attribute('datatypeLibrary', self.datatypes_uri)

            for p in self.params:
                p.dump(context)

            if self.except_pattern is not None:
                self.except_pattern.dump(context)
