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

    def select_next(self):
        self.model.select_index(self.model.index + 1)

    def select_previous(self):
        self.model.select_index(self.model.index - 1)

    def select_top(self):
        self.model.select_top()

    def select_bottom(self):
        self.model.select_bottom()

    def select_next_page(self):
        self.model.select_index(self.model.index + self.view.RESULTS_DISPLAY_MAX)

    def select_previous_page(self):
        self.model.select_index(self.model.index - self.view.RESULTS_DISPLAY_MAX)

    # ------------------------------------------------------------ #
    # Mark
    # ------------------------------------------------------------ #

    def toggle_mark(self):
        self.model.set_is_marked(not self.model.get_is_marked())

    def toggle_mark_and_next(self):
        self.toggle_mark()
        self.select_next()

    def __get_all_mark_indices(self):
        return xrange(self.model.results_count)

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

    # ------------------------------------------------------------ #
    # Text
    # ------------------------------------------------------------ #

    def delete_backward_char(self):
        if self.model.caret > 0:
            self.backward_char()
            self.delete_forward_char()

    def delete_backward_word(self):
        from re import search
        caret = self.model.caret
        if caret > 0:
            q = self.model.query
            qc = q[:caret]
            m = search(r'\S+', qc[::-1])
            self.model.query = qc[:-m.end()] + q[caret:]
            self.model.set_caret(caret - m.end())

    def delete_forward_char(self):
        caret = self.model.caret
        self.model.query = self.model.query[:caret] + self.model.query[caret + 1:]

    def delete_end_of_line(self):
        self.model.query = self.model.query[:self.model.caret]

    def clear_query(self):
        self.model.query = u""
        self.model.set_caret(0)

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
