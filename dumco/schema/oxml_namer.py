# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.utils.string_utils

import namer


class OxmlNamer(namer.CommonNamer):
    def _name_ct_from_parent_elem(self, parent_name, force_index):
        name = dumco.utils.string_utils.upper_first_letter(parent_name)
        assert not name.startswith('CT_')

        return 'CT_{0}{1}'.format(name, force_index)

    def _name_st_from_parent_elem(self, parent_name, force_index):
        name = dumco.utils.string_utils.upper_first_letter(parent_name)
        assert not name.startswith('ST_')

        return 'ST_{0}{1}'.format(name, force_index)

    def _name_st_from_parent_attr(self, parent_name, force_index):
        name = dumco.utils.string_utils.upper_first_letter(parent_name)
        assert not name.startswith('ST_')

        return 'ST_{0}{1}'.format(name, force_index)

    def _name_st_from_parent_ct(self, parent_name, force_index):
        name = dumco.utils.string_utils.upper_first_letter(parent_name)
        assert not name.startswith('ST_')

        return 'ST_BaseOf_{0}{1}'.format(name, force_index)

    def _name_st_from_parent_restriction_st(self, parent_name, force_index):
        name = dumco.utils.string_utils.upper_first_letter(parent_name)

        return '{0}Restr{1}'.format(name, force_index)

    def _name_st_from_parent_union_st(self, parent_name, index, force_index):
        name = dumco.utils.string_utils.upper_first_letter(parent_name)

        return '{0}Union{1}'.format(name, index)

    def _name_st_from_parent_list_st(self, parent_name, force_index):
        name = dumco.utils.string_utils.upper_first_letter(parent_name)

        return '{0}List{1}'.format(name, force_index)

    def _name_sequence(self, parent_name, index, force_index):
        return '{0}Seq{1}{2}'.format(parent_name, index, force_index)

    def _name_choice(self, parent_name, index, force_index):
        return '{0}Chc{1}{2}'.format(parent_name, index, force_index)

    def _name_all(self, parent_name, index, force_index):
        return '{0}All{1}{2}'.format(parent_name, index, force_index)
