# Distributed under the GPLv2 License; see accompanying file COPYING.

import dumco.utils.string_utils

import namer


class OxmlNamer(namer.CommonNamer):
    def _name_ct_from_parent_elem(self, parent_name, force_index):
        name = dumco.utils.string_utils.upper_first_letter(parent_name)
        assert not name.startswith('CT_')

        return 'CT_{}{}'.format(name, force_index)

    def _name_st_from_parent_elem(self, parent_name, force_index):
        name = dumco.utils.string_utils.upper_first_letter(parent_name)
        assert not name.startswith('ST_')

        return 'ST_{}{}'.format(name, force_index)

    def _name_st_from_parent_attr(self, parent_name, force_index):
        name = dumco.utils.string_utils.upper_first_letter(parent_name)
        assert not name.startswith('ST_')

        return 'ST_{}{}'.format(name, force_index)

    def _name_st_from_parent_ct(self, parent_name, force_index):
        name = dumco.utils.string_utils.upper_first_letter(parent_name)
        assert not name.startswith('ST_')

        return 'ST_BaseOf_{}{}'.format(name, force_index)

    def _name_st_from_parent_restriction_st(self, parent_name, force_index):
        name = dumco.utils.string_utils.upper_first_letter(parent_name)

        return '{}Restr{}'.format(name, force_index)

    def _name_st_from_parent_union_st(self, parent_name, index, force_index):
        name = dumco.utils.string_utils.upper_first_letter(parent_name)

        return '{}Union{}'.format(name, index)

    def _name_st_from_parent_list_st(self, parent_name, force_index):
        name = dumco.utils.string_utils.upper_first_letter(parent_name)

        return '{}List{}'.format(name, force_index)

    def _name_sequence(self, parent_name, index, force_index):
        return '{}Seq{}{}'.format(parent_name, index, force_index)

    def _name_choice(self, parent_name, index, force_index):
        return '{}Chc{}{}'.format(parent_name, index, force_index)

    def _name_all(self, parent_name, index, force_index):
        return '{}All{}{}'.format(parent_name, index, force_index)
