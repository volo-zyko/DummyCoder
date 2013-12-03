# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.schema.parsing.relaxng.element_factory

import rng_base
import rng_define
import rng_choice
import rng_interleave
import rng_start


def rng_grammar(attrs, parent_element, factory, grammar_path, all_grammars):
    grammar = RngGrammar(attrs, parent_element, grammar_path, factory)
    all_grammars[grammar_path] = grammar

    return (grammar, {
        'define': rng_define.rng_define,
        'div': factory.rng_div,
        # 'include': factory.noop_handler,
        'start': rng_start.rng_start,
    })


class RngGrammar(rng_base.RngBase):
    def __init__(self, attrs, parent_element, grammar_path, factory):
        super(RngGrammar, self).__init__(attrs, parent_element)

        self.known_prefices = factory.all_namespace_prefices
        self.grammar_path = grammar_path

        self.start = None
        self.start_combined = False
        self.defines = {}
        self.defines_combined = {}
        self.defines_used = set()

    def finalize(self, grammar, all_schemata, factory):
        for c in self.start.children:
            c.finalize(grammar, all_schemata, factory)

    def get_define(self, name):
        d = self.defines[name]
        self.defines_used.add(d)
        return d

    def add_start(self, start, grammar_path):
        assert (self.start is None or start.combine == '' or
                not self.start_combined), \
            'Multiple start elements in grammar without combine attribute'

        if self.start is None:
            self.start = start

            if start.combine == '':
                return start
            else:
                self.start_combined = True

                combine = self._make_combine(start, grammar_path)

                self.start.children.append(combine)
                return combine
        else:
            assert len(self.start.children) == 1, \
                'Only one child is expected in start element'

            combine = self.start.children[0]

            if start.combine != '':
                self.start_combined = True

                combine = self._make_combine(start, grammar_path)
                combine.children = self.start.children

                self.start.children = [combine]

            assert self.start_combined, \
                'There is more than one start element without combine attribute'
            assert (start.combine == '' or
                    (start.combine == 'choice' and
                     isinstance(combine, rng_choice.RngChoice)) or
                    (start.combine == 'interleave' and
                     isinstance(combine, rng_interleave.RngInterleave))), \
                'Different combine method in start is encountered'

            return combine

    def add_define(self, define, grammar_path):
        assert (define.name not in self.defines or define.combine == '' or
                not self.defines_combined[define.name]), \
            'Multiple define elements in grammar with ' \
            'same name and without combine attribute'

        if define.name not in self.defines:
            self.defines[define.name] = define

            if define.combine == '':
                return define
            else:
                self.defines_combined[define.name] = True

                combine = self._make_combine(define, grammar_path)

                self.defines[define.name] = combine
                return combine
        else:
            assert len(self.defines[define.name].children) == 1, \
                'Only one child is expected in define element'

            combine = self.defines[define.name].children[0]

            if define.combine != '':
                self.defines_combined[define.name] = True

                combine = self._make_combine(define, grammar_path)
                combine.children = self.defines[define.name].children

                self.defines[define.name].children = [combine]

            assert self.defines_combined[define.name], \
                'There is more than one define element without combine attribute'
            assert (define.combine == '' or
                    (define.combine == 'choice' and
                     isinstance(combine, rng_choice.RngChoice)) or
                    (define.combine == 'interleave' and
                     isinstance(combine, rng_interleave.RngInterleave))), \
                'Different combine method in define is encountered'

            return combine

    def _make_combine(self, parent, grammar_path):
        assert parent.combine == 'choice' or parent.combine == 'interleave', \
            'Combine can be either choice or interleave'

        if parent.combine == 'choice':
            return rng_choice.RngChoice({}, parent, grammar_path)
        elif parent.combine == 'interleave':
            return rng_interleave.RngInterleave({}, parent, grammar_path)

    def _dump_internals(self, fhandle, indent): # pragma: no cover
        fhandle.write(' xmlns="{}"'.format(
            dumco.schema.parsing.relaxng.element_factory.RNG_NAMESPACE))
        for (uri, prefix) in self.known_prefices.iteritems():
            fhandle.write(' xmlns:{}="{}"'.format(prefix, uri))
        fhandle.write('>\n')

        self.start.dump(fhandle, indent)

        for d in self.defines.itervalues():
            if d in self.defines_used:
                d.dump(fhandle, indent)

        return 3
