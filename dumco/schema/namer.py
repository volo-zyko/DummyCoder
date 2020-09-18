# Distributed under the GPLv2 License; see accompanying file COPYING.

import collections
import re

import checks
import enums
import tuples


class PatternParseException(BaseException):
    def __init__(self, pattern):
        self.pattern = pattern


def parse_name_patterns(text_patterns):
    # We expect here a string of the following format.
    # 'ct #aa#bb#, #ww#ee#i; st#qq#aa#g, #11#22#; eg#rr#tt#gi; ag#qqq#XXX#'.

    sub_matcher = re.compile('^#([^|]+)#([^|]+)#([ gi]*)$')

    (ct, st, eg, ag) = ([], [], [], [])
    for category_patterns in [x.strip() for x in text_patterns.split(';')]:
        category = category_patterns[:2]
        category_patterns = category_patterns[2:]

        if category == 'ct':
            subs = ct
        elif category == 'st':
            subs = st
        elif category == 'eg':
            subs = eg
        elif category == 'ag':
            subs = ag

        for sub_text_pattern in category_patterns.split(','):
            sub_text_pattern = sub_text_pattern.strip()

            match = sub_matcher.match(sub_text_pattern)
            if match is None:
                raise PatternParseException(sub_text_pattern)

            pattern = match.group(1).strip()
            replace = match.group(2).strip()
            options = match.group(3)

            re_flags = re.IGNORECASE if 'i' in options else 0
            apply_globally = 'g' in options

            subs.append((re.compile(pattern, re_flags),
                         replace, apply_globally))

    if not ct and not st and not eg and not ag:
        return None

    return (ct, st, eg, ag)


_NAME_HINT_NONE = -1
_NAME_HINT_CT = 0
_NAME_HINT_ST = 1
_NAME_HINT_ELEM = 2
_NAME_HINT_ATTR = 3


class Namer(object):
    SCHEMA_NAMING_NONE = 0
    # Camel-case with first lower letter.
    SCHEMA_NAMING_LCC = 1
    # Camel-case with first upper letter.
    SCHEMA_NAMING_UCC = 2
    # With underscores.
    SCHEMA_NAMING_WU = 4
    # With hyphens.
    SCHEMA_NAMING_WH = 8
    # With dots.
    SCHEMA_NAMING_WD = 16

    _NamingStats = collections.namedtuple(
        '_NamingStats', ['ct', 'st', 'elem', 'attr'])

    def __init__(self, naming_patterns):
        assert isinstance(naming_patterns, tuple) and len(naming_patterns) == 4
        self.ctype_patterns = naming_patterns[0]
        self.stype_patterns = naming_patterns[1]
        self.egroup_patterns = naming_patterns[2]
        self.agroup_patterns = naming_patterns[3]

        self.ctypes_counters = {}
        self.stypes_counters = {}
        self.egroups_counters = {}
        self.agroups_counters = {}

        self.naming_stats = self._NamingStats({}, {}, {}, {})

    def learn_naming(self, component):
        if checks.is_any(component):
            return

        (style, _) = _guess_naming(component.name)

        if checks.is_simple_type(component):
            c = self.naming_stats[_NAME_HINT_ST].get(style, 0)
            self.naming_stats[_NAME_HINT_ST][style] = c + 1
        elif checks.is_complex_type(component):
            c = self.naming_stats[_NAME_HINT_CT].get(style, 0)
            self.naming_stats[_NAME_HINT_CT][style] = c + 1
        elif checks.is_element(component):
            c = self.naming_stats[_NAME_HINT_ELEM].get(style, 0)
            self.naming_stats[_NAME_HINT_ELEM][style] = c + 1
        elif checks.is_attribute(component):
            c = self.naming_stats[_NAME_HINT_ATTR].get(style, 0)
            self.naming_stats[_NAME_HINT_ATTR][style] = c + 1
        else:
            assert False, 'Unexpected component'

    def populate_schema_with_naming(self, all_schemata):
        _populate_schema_with_naming(self, all_schemata)

    def name_ct(self, ct, parent):
        c = self.ctypes_counters.setdefault(ct.schema.target_ns, {})

        if ct.name is not None and not self.ctype_patterns:
            ct.name = _track_name(ct, ct.name, c)
            return

        if ct.name is None:
            assert checks.is_element(parent) and parent.name is not None
            (style, words) = self._parse_name(parent.name, _NAME_HINT_CT)
            words.extend(['complex', 'type'])
        else:
            (style, words) = self._parse_name(ct.name, _NAME_HINT_CT)

        ct.name = self._apply_patterns(ct, words, c, self.ctype_patterns, style)

    def name_st(self, st, parent):
        c = self.stypes_counters.setdefault(st.schema.target_ns, {})

        if st.name is not None and not self.stype_patterns:
            st.name = _track_name(st, st.name, c)
            return

        if st.name is None and checks.is_text(parent):
            (style, words) = self._parse_name('text', _NAME_HINT_ST)
            if checks.is_union_type(st):
                words.extend(['union', 'type'])
            elif checks.is_list_type(st):
                words.extend(['list', 'type'])
            else:
                words.extend(['simple', 'type'])
        elif st.name is None:
            assert parent.name is not None
            if checks.is_element(parent) or checks.is_attribute(parent):
                (style, words) = self._parse_name(parent.name, _NAME_HINT_ST)
                if checks.is_union_type(st):
                    words.extend(['union', 'type'])
                elif checks.is_list_type(st):
                    words.extend(['list', 'type'])
                else:
                    words.extend(['simple', 'type'])
            elif checks.is_complex_type(parent):
                (style, words) = self._parse_name(parent.name, _NAME_HINT_ST)
                words.extend(['simple', 'content'])
            elif checks.is_union_type(parent):
                (style, words) = self._parse_name(parent.name, _NAME_HINT_ST)
                if checks.is_union_type(st):
                    words.extend(['member', 'union', 'type'])
                elif checks.is_list_type(st):
                    words.extend(['member', 'list', 'type'])
                else:
                    words.extend(['member', 'simple', 'type'])
            elif checks.is_list_type(parent):
                (style, words) = self._parse_name(parent.name, _NAME_HINT_ST)
                if checks.is_union_type(st):
                    words.extend(['item', 'union', 'type'])
                elif checks.is_list_type(st):
                    words.extend(['item', 'list', 'type'])
                else:
                    words.extend(['item', 'simple', 'type'])
            elif checks.is_restriction_type(parent):
                (style, words) = self._parse_name(parent.name, _NAME_HINT_ST)
            else:
                assert False, 'Unexpected parent for simple type'
        else:
            (style, words) = self._parse_name(st.name, _NAME_HINT_ST)

        st.name = self._apply_patterns(st, words, c, self.stype_patterns, style)

    def name_egroup(self, particle_parent):
        assert checks.is_particle(particle_parent)

        elem = particle_parent.term
        c = self.egroups_counters.setdefault(elem.schema.target_ns, {})

        assert elem.name is not None
        (style, words) = self._parse_name(elem.name, _NAME_HINT_ELEM)
        words.append('group')

        return self._apply_patterns(
            tuples.HashableParticle(particle_parent, None),
            words, c, self.egroup_patterns, style)

    def name_agroup(self, attr_use_parent):
        assert checks.is_attribute_use(attr_use_parent)

        attr = attr_use_parent.attribute
        c = self.agroups_counters.setdefault(attr.schema.target_ns, {})

        assert attr.name is not None
        (style, words) = self._parse_name(attr.name, _NAME_HINT_ATTR)
        words.append('group')

        return self._apply_patterns(
            tuples.HashableAttributeUse(attr_use_parent, None),
            words, c, self.agroup_patterns, style)

    def _parse_name(self, name, hint):
        (_, words) = _guess_naming(name)

        stats = list(self.naming_stats[hint].iteritems())
        if stats:
            style = max(stats, key=lambda x: x[1])[0]
            return (style, words)

        return (Namer.SCHEMA_NAMING_UCC, words)

    def _apply_patterns(self, key_component, words, counters, patterns, style):
        if patterns:
            new_name = '-'.join(words)

            for (pattern, replace, g) in patterns:
                new_name = pattern.sub(replace, new_name, count=0 if g else 1)
        else:
            if (style & Namer.SCHEMA_NAMING_UCC or
                    style & Namer.SCHEMA_NAMING_LCC):
                words[1:] = map(lambda x: x.capitalize(), words[1:])
            if not style & Namer.SCHEMA_NAMING_LCC:
                words[0] = words[0].capitalize()

            new_name = _get_join_char(style).join(words)

        return _track_name(key_component, new_name, counters)


STEM_PARSER = re.compile('([-._a-zA-Z0-9]*?)([0-9]*)$')


def _track_name(key_component, name, counters):
    m = STEM_PARSER.match(name)
    assert m is not None

    (stem, name_id) = m.group(1, 2)
    name_id = 0 if name_id == '' else int(name_id)

    count_tracker = counters.setdefault(stem, {})

    if key_component not in count_tracker:
        if name_id in count_tracker.itervalues():
            for name_id in xrange(0, 2 ** 30):
                if name_id not in count_tracker.itervalues():
                    count_tracker[key_component] = name_id
                    break
        else:
            count_tracker[key_component] = name_id

    return stem if name_id == 0 else '{}{}'.format(stem, name_id)


def _get_join_char(style):
    join_char_map = {
        1: '',          # ucc
        2: '',          # lcc
        3: None,        # ucc|lcc
        4: '_',         # wu
        5: '',          # ucc|wu
        6: '',          # lcc|wu
        7: None,        # ucc|lcc|wu
        8: '-',         # wh
        9: '',          # ucc|wh
        10: '',         # lcc|wh
        11: None,       # ucc|lcc|wh
        12: '-',        # wu|wh
        13: '-',        # ucc|wu|wh
        14: '-',        # lcc|wu|wh
        15: None,       # ucc|lcc|wu|wh
        16: '.',        # wd
        17: '',         # ucc|wd
        18: '',         # lcc|wd
        19: None,       # ucc|lcc|wd
        20: '-',        # wu|wd
        21: '-',        # ucc|wu|wd
        22: '-',        # lcc|wu|wd
        23: None,       # ucc|lcc|wu|wd
        24: '-',        # wh|wd
        25: '-',        # ucc|wh|wd
        26: '-',        # lcc|wh|wd
        27: None,       # ucc|lcc|wh|wd
        28: '-',        # wu|wh|wd
        29: '-',        # ucc|wu|wh|wd
        30: '-',        # lcc|wu|wh|wd
        31: None,       # ucc|lcc|wu|wh|wd
    }

    return join_char_map[style]


def _guess_naming(name):
    words = []
    style = Namer.SCHEMA_NAMING_NONE

    current_word = []
    prev_char = None
    add_word = False
    for x in name:
        if x.isupper() and prev_char is None:
            current_word.append(x)
            prev_char = x
            continue
        elif x.isupper() or x.isdigit():
            if prev_char is None:
                current_word.append(x)
                prev_char = x
                continue
            elif (prev_char.isupper() or prev_char.isdigit() or
                    (prev_char.islower() and x.isdigit())):
                # Looks like abbreviation.
                current_word.append(x)
                prev_char = x
                continue
            elif prev_char.islower():
                style |= Namer.SCHEMA_NAMING_UCC | Namer.SCHEMA_NAMING_LCC
                add_word = True
        elif x.islower():
            current_word.append(x)
            prev_char = x
            continue
        elif x == '_':
            assert len(current_word) > 0
            style |= Namer.SCHEMA_NAMING_WU
            add_word = True
            x = None
        elif x == '-':
            assert len(current_word) > 0
            style |= Namer.SCHEMA_NAMING_WH
            add_word = True
            x = None
        elif x == '.':
            assert len(current_word) > 0
            style |= Namer.SCHEMA_NAMING_WD
            add_word = True
            x = None
        else:
            if ((prev_char.isupper() or prev_char.isdigit()) and
                    len(current_word) > 2):
                words.append(''.join(current_word[:-2]))
                current_word = [current_word[-1]]

            current_word.append(x)
            prev_char = x
            continue

        if add_word:
            words.append(''.join(current_word))
            if x is None:
                current_word = []
                prev_char = None
            else:
                current_word = [x]
                prev_char = x
            add_word = False

    if current_word:
        words.append(''.join(current_word))

    cc = Namer.SCHEMA_NAMING_UCC | Namer.SCHEMA_NAMING_LCC
    if (style & cc) == cc:
        if words[0][0].isupper() and not words[0].isupper():
            # Remains UCC
            style &= ~Namer.SCHEMA_NAMING_LCC
        else:
            # Remains LCC
            style &= ~Namer.SCHEMA_NAMING_UCC
    elif style == Namer.SCHEMA_NAMING_NONE:
        if name[0].isupper():
            style = Namer.SCHEMA_NAMING_UCC
        else:
            style = Namer.SCHEMA_NAMING_LCC

    return (style, words)


def _populate_schema_with_naming(namer, all_schemata):
    visited_cts = set()

    unnamed_sts = []
    unnamed_cts = []

    def traverse_complex_type(ct, parent):
        if ct in visited_cts:
            return

        if ct.name is None:
            unnamed_cts.append((ct, parent))
        else:
            namer.learn_naming(ct)
            namer.name_ct(ct, parent)
        ct.schema.complex_types.append(ct)
        visited_cts.add(ct)

        for child in enums.enum_flat(ct):
            if checks.is_attribute_use(child):
                if checks.is_any(child.attribute):
                    continue

                traverse_simple_type(child.attribute.type, child.attribute)
            elif checks.is_particle(child):
                if checks.is_any(child.term):
                    continue

                if checks.is_complex_type(child.term.type):
                    traverse_complex_type(child.term.type, child.term)
                elif checks.is_simple_type(child.term.type):
                    traverse_simple_type(child.term.type, child.term)
            elif checks.is_text(child):
                traverse_simple_type(child.type, child)

    def traverse_simple_type(st, parent):
        if checks.is_native_type(st):
            assert st.name is not None
            return

        if st.name is None:
            unnamed_sts.append((st, parent))
        else:
            namer.learn_naming(st)
            namer.name_st(st, parent)
        st.schema.simple_types.append(st)

        if checks.is_list_type(st):
            for item in st.listitems:
                traverse_simple_type(item.type, st)
        elif checks.is_union_type(st):
            for member in st.union:
                traverse_simple_type(member, st)

    for schema in all_schemata:
        for elem in schema.elements:
            if checks.is_complex_type(elem.type):
                traverse_complex_type(elem.type, elem)
            elif checks.is_simple_type(elem.type):
                traverse_simple_type(elem.type, elem)

    for (ct, parent) in unnamed_cts:
        namer.name_ct(ct, parent)

    for (st, parent) in unnamed_sts:
        namer.name_st(st, parent)

    for schema in all_schemata:
        schema.simple_types.sort(key=lambda s: s.name)
        schema.complex_types.sort(key=lambda c: c.name)
        schema.elements.sort(key=lambda e: e.name)
