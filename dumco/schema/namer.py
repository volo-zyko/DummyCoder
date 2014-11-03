# Distributed under the GPLv2 License; see accompanying file COPYING.

import collections
import re


class PatternParseException(BaseException):
    def __init__(self, pattern):
        self.pattern = pattern


def parse_name_patterns(text_patterns):
    # We expect here a string of the following format.
    # 'ct #aa#bb#, #ww#ee#i; st#qq#aa# g, #11#22#; eg#rr#tt#gi; ag#qqq#XXX#'.

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


NAME_HINT_NONE = -1
NAME_HINT_CT = 0
NAME_HINT_ST = 1
NAME_HINT_EG = 2
NAME_HINT_AG = 3
NAME_HINT_ELEM = 4
NAME_HINT_ATTR = 5


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
        '_NamingStats', ['ct', 'st', 'eg', 'ag', 'elem', 'attr'])

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

        self.naming_stats = self._NamingStats({}, {}, {}, {}, {}, {})

    def learn_naming(self, assigned_name, hint):
        assert assigned_name is not None
        assert NAME_HINT_NONE < hint and hint <= NAME_HINT_ATTR

        (style, _) = _guess_naming(assigned_name)

        c = self.naming_stats[hint].get(style, 0)
        self.naming_stats[hint][style] = c + 1

    def name_ct(self, name, ns, parent):
        c = self.ctypes_counters.setdefault(ns, {})
        if not self.ctype_patterns:
            return self._generate_uniq_name(c, parent, [NAME_HINT_CT])

        return self._apply_patterns(name, c, self.ctype_patterns, NAME_HINT_CT)

    def name_st(self, name, ns, parent):
        c = self.stypes_counters.setdefault(ns, {})
        if not self.stype_patterns:
            return self._generate_uniq_name(c, parent, [NAME_HINT_ST])

        return self._apply_patterns(name, c, self.stype_patterns, NAME_HINT_ST)

    def name_egroup(self, name, ns, parent):
        c = self.egroups_counters.setdefault(ns, {})
        if not self.egroup_patterns:
            return self._generate_uniq_name(
                c, parent, [NAME_HINT_EG, NAME_HINT_ELEM])

        return self._apply_patterns(name, c, self.egroup_patterns, NAME_HINT_EG)

    def name_agroup(self, name, ns, parent):
        c = self.agroups_counters.setdefault(ns, {})
        if not self.agroup_patterns:
            return self._generate_uniq_name(
                c, parent, [NAME_HINT_AG, NAME_HINT_ATTR])

        return self._apply_patterns(name, c, self.agroup_patterns, NAME_HINT_AG)

    def _generate_uniq_name(self, counters, parent, hints):
        if hasattr(parent, 'name'):
            assert parent.name is not None
            parent_name = parent.name
        else:
            parent_name = parent.__class__.__name__

        words = _get_name_words(parent_name, hints[0])

        stats = []
        for hint in hints:
            stats = list(self.naming_stats[hint].iteritems())

        if stats:
            style = max(stats, key=lambda x: x[1])[0]
        else:
            style = Namer.SCHEMA_NAMING_UCC

        if style & Namer.SCHEMA_NAMING_UCC or style & Namer.SCHEMA_NAMING_LCC:
            words[1:] = map(lambda x: x.capitalize(), words[1:])
        if not style & Namer.SCHEMA_NAMING_LCC:
            words[0] = words[0].capitalize()

        name = _get_join_char(style).join(words)

        return _finalize_name(name, counters)

    def _apply_patterns(self, old_name, counters, patterns, hint):
        assert old_name is not None

        words = _get_name_words(old_name, hint)
        name = '-'.join(words)

        for (pattern, replace, g) in patterns:
            name = pattern.sub(replace, name, count=0 if g else 1)

        return _finalize_name(name, counters)


def _get_name_words(name, hint):
    assert NAME_HINT_NONE < hint and hint <= NAME_HINT_AG

    (_, words) = _guess_naming(name)

    if hint == NAME_HINT_CT:
        words.extend(['complex', 'type'])
    elif hint == NAME_HINT_ST:
        words.extend(['simple', 'type'])
    elif hint == NAME_HINT_EG:
        words.extend(['element', 'group'])
    elif hint == NAME_HINT_AG:
        words.extend(['attribute', 'group'])

    return words


def _finalize_name(name, counters):
    c = counters.get(name, 0)

    while True:
        new_name = name if c == 0 else name + str(c)
        c += 1

        if new_name not in counters:
            counters[name] = c
            return new_name


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
