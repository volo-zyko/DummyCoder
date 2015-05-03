# Distributed under the GPLv2 License; see accompanying file COPYING.

import os.path
import StringIO

from dumco.utils.decorators import method_once

import dumco.schema.checks
from dumco.schema.rng_types import RNG_NAMESPACE

import dumco.schema.parsing.xml_parser

import base
import rng_define
import rng_choice
import rng_element
import rng_interleave
import rng_start
import utils


def rng_grammar(attrs, parent_element, builder, grammar_path, all_grammars):
    grammar = RngGrammar(attrs, grammar_path, builder)
    all_grammars[grammar_path] = grammar

    return (grammar, {
        'define': rng_define.rng_define,
        'div': builder.rng_div,
        'include': RngGrammar.rng_include,
        'start': rng_start.rng_start,
    })


class RngGrammar(base.RngBase):
    def __init__(self, attrs, grammar_path, builder):
        super(RngGrammar, self).__init__(attrs)

        # Temporaries.
        self.known_prefixes = builder.all_namespace_prefixes
        self.grammar_path = grammar_path
        # In start_combined, defines_combined members we track combine
        # attribute in start and define elements.
        self.start_combined = False
        self.defines_combined = {}
        # defines member contains define elements from original grammar.
        self.defines = {}
        self.element_counter = 1

        self.start = None
        # We reassign 'define' names after loading and here we track
        # correspondence between new names and elements themselves.
        self.named_elements = {}

    @method_once
    def finalize(self, grammar, builder):
        # Collect children in defines without finalizing them. This
        # prevents finalization loops.
        for d in self.defines.itervalues():
            d.prefinalize(grammar)

        # Finalize everything from grammar start. This also collects
        # all elements in a grammar and assigns them new names.
        self.start.finalize(grammar, builder)

        # Finish finalization of elements. Elements are not finalized when
        # start is finalized because this might create infinite finalization
        # loops.
        element_set = set(self.named_elements.itervalues())
        remaining = element_set
        while remaining:
            for e in sorted(remaining, key=lambda e: e.define_name):
                e.finalize(grammar, builder)

            new_element_set = set(self.named_elements.itervalues())
            remaining = new_element_set - element_set
            element_set = new_element_set

        super(RngGrammar, self).finalize(grammar, builder)

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

                combine = _make_combine(start.combine)

                self.start.children.append(combine)
                return combine
        else:
            assert len(self.start.children) == 1, \
                'Only one child is expected in start element'

            combine = self.start.children[0]

            if not self.start_combined and start.combine != '':
                self.start_combined = True

                combine = _make_combine(start.combine)
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

                combine = _make_combine(define.combine)

                self.defines[define.name].children.append(combine)
                return combine
        else:
            assert len(self.defines[define.name].children) == 1, \
                'Only one child is expected in define element'

            combine = self.defines[define.name].children[0]

            if not self.defines_combined[define.name] and define.combine != '':
                self.defines_combined[define.name] = True

                combine = _make_combine(define.combine)
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
    def rng_include(attrs, parent_element, builder,
                    grammar_path, all_grammars):
        # Restart parsing with a new rng.
        include_logic = _RngIncludeLogic(grammar_path, builder)
        rng_root = include_logic.include_xml(grammar_path)
        all_grammars[grammar_path] = None
        builder.reset()

        raise dumco.schema.parsing.xml_parser.ParseRestart(
            StringIO.StringIO(rng_root.toxml('utf-8')))

    def dump(self, context):
        with utils.RngTagGuard('grammar', context):
            context.define_namespace('', RNG_NAMESPACE)

            for (uri, prefix) in sorted(self.known_prefixes.iteritems()):
                if not dumco.schema.checks.is_xml_namespace(uri):
                    context.define_namespace(prefix, uri)

            self.start.dump(context)

            for e in sorted(self.named_elements.itervalues(),
                            key=lambda e: e.define_name):
                assert isinstance(e, rng_element.RngElement), \
                    'Only elements should be defined in RNG dump'

                with utils.RngTagGuard('define', context):
                    context.add_attribute('name', e.define_name)
                    e.dump(context)


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


def _make_combine(combine_type):
    assert combine_type == 'choice' or combine_type == 'interleave', \
        'Combine can be either choice or interleave'

    if combine_type == 'choice':
        return rng_choice.RngChoicePattern()
    elif combine_type == 'interleave':
        return rng_interleave.RngInterleave()
