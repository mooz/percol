# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import six

class SelectorCommand(object):
    """
    Wraps up SelectorModel and provides advanced commands
    """
    def __init__(self, model, view):
        self.model = model
        self.view = view

    # ------------------------------------------------------------ #
    # Selection
    # ------------------------------------------------------------ #

    # Line

    def select_successor(self):
        self.model.select_index(self.model.index + 1)

    def select_predecessor(self):
        self.model.select_index(self.model.index - 1)

    def select_next(self):
        if self.view.results_top_down:
            self.select_successor()
        else:
            self.select_predecessor()

    def select_previous(self):
        if self.view.results_top_down:
            self.select_predecessor()
        else:
            self.select_successor()

    # Top / Bottom

    def select_top(self):
        if self.view.results_top_down:
            self.model.select_top()
        else:
            self.model.select_bottom()

    def select_bottom(self):
        if self.view.results_top_down:
            self.model.select_bottom()
        else:
            self.model.select_top()

    # Page

    def select_successor_page(self):
        self.model.select_index(self.model.index + self.view.RESULTS_DISPLAY_MAX)

    def select_predecessor_page(self):
        self.model.select_index(self.model.index - self.view.RESULTS_DISPLAY_MAX)

    def select_next_page(self):
        if self.view.results_top_down:
            self.select_successor_page()
        else:
            self.select_predecessor_page()

    def select_previous_page(self):
        if self.view.results_top_down:
            self.select_predecessor_page()
        else:
            self.select_successor_page()

    # ------------------------------------------------------------ #
    # Mark
    # ------------------------------------------------------------ #

    def toggle_mark(self):
        self.model.set_is_marked(not self.model.get_is_marked())

    def toggle_mark_and_next(self):
        self.toggle_mark()
        self.select_successor()

    def __get_all_mark_indices(self):
        return six.moves.range(self.model.results_count)

    def mark_all(self):
        for mark_index in self.__get_all_mark_indices():
            self.model.set_is_marked(True, mark_index)

    def unmark_all(self):
        for mark_index in self.__get_all_mark_indices():
            self.model.set_is_marked(False, mark_index)

    def toggle_mark_all(self):
        for mark_index in self.__get_all_mark_indices():
            self.model.set_is_marked(not self.model.get_is_marked(mark_index), mark_index)

    # ------------------------------------------------------------ #
    # Caret
    # ------------------------------------------------------------ #

    def beginning_of_line(self):
        self.model.set_caret(0)

    def end_of_line(self):
        self.model.set_caret(len(self.model.query))

    def backward_char(self):
        self.model.set_caret(self.model.caret - 1)

    def forward_char(self):
        self.model.set_caret(self.model.caret + 1)

    def _get_backward_word_begin(self):
        from re import match
        skippable_substring = match(r'\s*\S*', self.model.query[:self.model.caret][::-1])
        return self.model.caret - skippable_substring.end()

    def _get_forward_word_end(self):
        from re import match
        skippable_substring = match(r'\s*\S*', self.model.query[self.model.caret:])
        return self.model.caret + skippable_substring.end()

    def backward_word(self):
        self.model.set_caret(self._get_backward_word_begin())

    def forward_word(self):
        self.model.set_caret(self._get_forward_word_end())

    # ------------------------------------------------------------ #
    # Text
    # ------------------------------------------------------------ #

    def delete_backward_char(self):
        if self.model.caret > 0:
            self.backward_char()
            self.delete_forward_char()

    def delete_forward_char(self):
        caret = self.model.caret
        self.model.query = self.model.query[:caret] + self.model.query[caret + 1:]

    def delete_backward_word(self):
        backword_word_begin = self._get_backward_word_begin()
        backword_word_end = self.model.caret
        self.model.query = self.model.query[:backword_word_begin] + self.model.query[backword_word_end:]
        self.model.set_caret(backword_word_begin)

    def delete_forward_word(self):
        forward_word_begin = self.model.caret
        forward_word_end = self._get_forward_word_end()
        self.model.query = self.model.query[:forward_word_begin] + self.model.query[forward_word_end:]
        self.model.set_caret(forward_word_begin)

    def delete_end_of_line(self):
        self.model.query = self.model.query[:self.model.caret]

    def clear_query(self):
        self.model.query = u""
        self.model.set_caret(0)

    def transpose_chars(self):
        caret = self.model.caret
        qlen = len(self.model.query)
        if qlen <= 1:
            self.end_of_line()
        elif caret == 0:
            self.forward_char()
            self.transpose_chars()
        elif caret == qlen:
            self.backward_char()
            self.transpose_chars()
        else:
            self.model.query = self.model.query[:caret - 1] + \
                               self.model.query[caret] + \
                               self.model.query[caret - 1] + \
                               self.model.query[caret + 1:]
            self.forward_char()

    def unnarrow(self):
        """
        Clears the query, but keeps the current line selected. Useful to
        show context around a search match.
        """
        try:
            original_index = self.model.results[self.model.index][2]
        except IndexError:
            original_index = 0
        self.clear_query()
        self.model.do_search("")
        self.model.select_index(original_index)

    # ------------------------------------------------------------ #
    # Text > kill
    # ------------------------------------------------------------ #

    def kill_end_of_line(self):
        self.model.killed = self.model.query[self.model.caret:]
        self.model.query  = self.model.query[:self.model.caret]

    killed = None                  # default
    def yank(self):
        if self.model.killed:
            self.model.insert_string(self.model.killed)

    # ------------------------------------------------------------ #
    # Finder
    # ------------------------------------------------------------ #

    def specify_case_sensitive(self, case_sensitive):
        self.model.finder.case_insensitive = not case_sensitive
        self.model.force_search()

    def toggle_case_sensitive(self):
        self.model.finder.case_insensitive = not self.model.finder.case_insensitive
        self.model.force_search()

    def specify_split_query(self, split_query):
        self.model.finder.split_query = split_query
        self.model.force_search()

    def toggle_split_query(self):
        self.model.finder.split_query = not self.model.finder.split_query
        self.model.force_search()

    def specify_finder(self, preferred_finder_class):
        self.model.remake_finder(preferred_finder_class)
        self.model.force_search()

    def toggle_finder(self, preferred_finder_class):
        if self.model.finder.__class__ == preferred_finder_class:
            self.model.remake_finder(self.model.original_finder_class)
        else:
            self.model.remake_finder(preferred_finder_class)
        self.model.force_search()
