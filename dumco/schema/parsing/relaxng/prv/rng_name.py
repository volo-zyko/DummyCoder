# Distributed under the GPLv2 License; see accompanying file COPYING.

import base
import utils


def create_name(qname, factory):
    (ns, name) = factory.parse_qname(qname)
    ns = factory.get_ns() if ns is None else ns
    name = None if name == '' else name

    return RngName(ns, name, _is_qualified(ns, factory))


def rng_name(attrs, parent_element, factory, grammar_path, all_grammars):
    parent_element.children.append(create_name('', factory))

    return (parent_element.children[-1], {})


class RngName(base.RngBase):
    def __init__(self, ns, name, qualified=None):
        super(RngName, self).__init__()

        self.ns = ns
        self.name = name

        # It's necessary for conversion to dumco model.
        self.qualified = qualified

    def append_text(self, text, factory):
        assert self.name is None, \
            'Name is defined as both attribute and name class'

        name_obj = create_name(text, factory)

        self.ns = name_obj.ns
        self.name = name_obj.name
        self.qualified = name_obj.qualified

    def dump(self, context):
        with utils.RngTagGuard('name', context):
            context.add_attribute('ns', self.ns)
            context.add_text(self.name)


def _is_qualified(self, ns, factory):
    if ns is not None:
        return ns != ''

    return factory.get_ns() != ''
