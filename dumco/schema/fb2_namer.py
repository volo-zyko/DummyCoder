# Distributed under the GPLv2 License; see accompanying file COPYING.

import namer


class Fb2Namer(namer.CommonNamer):
    def _name_ct_from_parent_elem(self, parent_name, force_index):
        return '{0}ElemCt{1}'.format(parent_name, force_index)

    def _name_st_from_parent_elem(self, parent_name, force_index):
        return '{0}ElemSt{1}'.format(parent_name, force_index)

    def _name_st_from_parent_attr(self, parent_name, force_index):
        return '{0}AttrSt{1}'.format(parent_name, force_index)

    def _name_st_from_parent_ct(self, parent_name, force_index):
        return '{0}StBaseOf{1}'.format(parent_name, force_index)

    def _name_st_from_parent_restriction_st(self, parent_name, force_index):
        return '{0}Restr{1}'.format(parent_name, force_index)

    def _name_st_from_parent_union_st(self, parent_name, index, force_index):
        return '{0}Union{1}'.format(parent_name, index)

    def _name_st_from_parent_list_st(self, parent_name, force_index):
        return '{0}List{1}'.format(parent_name, force_index)

    def _name_sequence(self, parent_name, index, force_index):
        return '{0}Seq{1}{2}'.format(parent_name, index, force_index)

    def _name_choice(self, parent_name, index, force_index):
        return '{0}Chc{1}{2}'.format(parent_name, index, force_index)

    def _name_all(self, parent_name, index, force_index):
        return '{0}All{1}{2}'.format(parent_name, index, force_index)
