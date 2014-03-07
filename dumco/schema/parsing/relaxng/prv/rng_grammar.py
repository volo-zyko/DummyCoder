# Distributed under the GPLv2 License; see accompanying file COPYING.

import os.path
import StringIO

from dumco.utils.decorators import method_once

import dumco.schema.checks
from dumco.schema.rng_types import RNG_NAMESPACE

import dumco.schema.parsing.xml_parser

import rng_base
import rng_define
import rng_choice
import rng_element
import rng_interleave
import rng_start


def rng_grammar(attrs, parent_element, factory, grammar_path, all_grammars):
    grammar = RngGrammar(attrs, parent_element, grammar_path, factory)
    all_grammars[grammar_path] = grammar

    return (grammar, {
        'define': rng_define.rng_define,
        'div': factory.rng_div,
        'include': RngGrammar.rng_include,
        'start': rng_start.rng_start,
    })


class RngGrammar(rng_base.RngBase):
    def __init__(self, attrs, parent_element, grammar_path, factory):
        super(RngGrammar, self).__init__(attrs, parent_element)

        # Temporaries.
        self.known_prefixes = factory.all_namespace_prefixes
        self.grammar_path = grammar_path
        self.start_combined = False
        self.defines = {}
        self.defines_combined = {}
        self.element_counter = 1

        self.start = None
        self.elements = []

    @method_once
    def finalize(self, grammar, factory):
        # Collect children in defines without finalizing them. This
        # prevents finalization loops.
        for d in self.defines.itervalues():
            d.prefinalize(grammar)

        # Finalize everything from grammar start. This also collects
        # all elements in a grammar and assigns them new names.
        self.start.finalize(grammar, factory)

        self.elements.sort(key=lambda e: e.define_name)

        # Finish finalization of elements. Elements are not finalized when
        # start is finalized because this might create infinite finalization
        # loops.
        for e in self.elements:
            e.finalize(grammar, factory)

        super(RngGrammar, self).finalize(grammar, factory)

    def add_start(self, start):
        assert (self.start is None or start.combine == '' or
                not self.start_combined), \
            'Multiple start elements in grammar without combine attribute'

        if self.start is None:
            self.start = start

            if start.combine == '':
                return start
            else:
                self.start_combined = True

                combine = _make_combine(start.combine, start)

                self.start.children.append(combine)
                return combine
        else:
            assert len(self.start.children) == 1, \
                'Only one child is expected in start element'

            combine = self.start.children[0]

            if not self.start_combined and start.combine != '':
                self.start_combined = True

                combine = _make_combine(start.combine, self.start)
                combine.children = self.start.children

                self.start.children = [combine]

            assert self.start_combined, \
                'There is more than one start element ' \
                'without combine attribute'
            assert (start.combine == '' or
                    (start.combine == 'choice' and
                     isinstance(combine, rng_choice.RngChoicePattern))
                    or
                    (start.combine == 'interleave' and
                     isinstance(combine, rng_interleave.RngInterleave))), \
                'Different combine method in start is encountered'

            return combine

    def get_define(self, name):
        return self.defines[name]

    def add_define(self, define):
        assert (define.name not in self.defines or define.combine == '' or
                not self.defines_combined[define.name]), \
            'Multiple define elements in grammar with ' \
            'same name and without combine attribute'

        if define.name not in self.defines:
            self.defines[define.name] = define

            if define.combine == '':
                self.defines_combined[define.name] = False
                return define
            else:
                self.defines_combined[define.name] = True

                combine = _make_combine(define.combine, define)

                self.defines[define.name].children.append(combine)
                return combine
        else:
            assert len(self.defines[define.name].children) == 1, \
                'Only one child is expected in define element'

            combine = self.defines[define.name].children[0]

            if not self.defines_combined[define.name] and define.combine != '':
                self.defines_combined[define.name] = True

                combine = _make_combine(
                    define.combine, self.defines[define.name])
                combine.children = self.defines[define.name].children

                self.defines[define.name].children = [combine]

            assert self.defines_combined[define.name], \
                'There is more than one define element ' \
                'without combine attribute'
            assert (define.combine == '' or
                    (define.combine == 'choice' and
                     isinstance(combine, rng_choice.RngChoicePattern))
                    or
                    (define.combine == 'interleave' and
                     isinstance(combine, rng_interleave.RngInterleave))), \
                'Different combine method in define is encountered'

            return combine

    @staticmethod
    def rng_include(attrs, parent_element, factory,
                    grammar_path, all_grammars):
        # Restart parsing with a new rng.
        include_logic = _RngIncludeLogic(grammar_path, factory)
        rng_root = include_logic.include_xml(grammar_path)
        all_grammars[grammar_path] = None
        factory.reset()

        raise dumco.schema.parsing.xml_parser.ParseRestart(
            StringIO.StringIO(rng_root.toxml('utf-8')))

    def _dump_internals(self, fhandle, indent):
        fhandle.write(' xmlns="{}"'.format(RNG_NAMESPACE))
        for (uri, prefix) in sorted(self.known_prefixes.iteritems()):
            if not dumco.schema.checks.is_xml_namespace(uri):
                fhandle.write(' xmlns:{}="{}"'.format(prefix, uri))
        fhandle.write('>\n')

        self.start.dump(fhandle, indent)

        for e in self.elements:
            assert isinstance(e, rng_element.RngElement), \
                'Only elements should be defined in RNG dump'

            space = ' ' * indent
            fhandle.write('{}<define name="{}">\n'.format(space,
                                                          e.define_name))
            e.dump(fhandle, indent + self._tab)
            fhandle.write('{}</define>\n'.format(space))

        return rng_base.RngBase._CLOSING_TAG


class _RngIncludeLogic(dumco.schema.parsing.xml_parser.IncludeLogic):
    def _is_rng_node(self, node, name):
        return (node.nodeType == node.ELEMENT_NODE and
                RNG_NAMESPACE == node.namespaceURI and
                node.localName == name)

    def _is_root_node(self, node):
        return self._is_rng_node(node, 'grammar')

    def _is_include_node(self, node):
        return self._is_rng_node(node, 'include')

    def _get_included_path(self, node, curr_path):
        assert node.hasAttribute('href'), 'Include without href attribute'

        location = node.getAttribute('href')

        return os.path.realpath(
            os.path.join(os.path.dirname(curr_path), location))

    def _copy_included(self, including_dom, include_node,
                       included_root, included_path):
        include_node.tagName = 'div'
        include_node.removeAttribute('href')

        new_node = including_dom.importNode(included_root, True)
        new_node.tagName = 'div'

        include_node.insertBefore(new_node, include_node.firstChild)


def _make_combine(combine_type, parent):
    assert combine_type == 'choice' or combine_type == 'interleave', \
        'Combine can be either choice or interleave'

    if combine_type == 'choice':
        return rng_choice.RngChoicePattern({}, parent)
    elif combine_type == 'interleave':
        return rng_interleave.RngInterleave({}, parent)
