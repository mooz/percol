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
from percol import display, debug

class SelectorModel(object):
    def __init__(self,
                 percol, collection, finder,
                 query = None, caret = None, index = None):
        self.original_finder_class = finder
        self.percol = percol
        self.finder = finder(collection)
        self.setup_results(query)
        self.setup_caret(caret)
        self.setup_index(index)

    # ============================================================ #
    # Pager attributes
    # ============================================================ #

    @property
    def absolute_index(self):
        return self.index

    @property
    def results_count(self):
        return len(self.results)

    # ============================================================ #
    # Initializer
    # ============================================================ #

    def setup_results(self, query):
        self.query   = self.old_query = query or u""
        self.results = self.finder.get_results(self.query)
        self.marks   = {}

    def setup_caret(self, caret):
        if isinstance(caret, six.string_types):
            try:
                caret = int(caret)
            except ValueError:
                caret = None
        if caret is None or caret < 0 or caret > display.screen_len(self.query):
            caret = display.screen_len(self.query)
        self.caret = caret

    def setup_index(self, index):
        self.index = 0
        if index is None or index == "first":
            self.select_top()
        elif index == "last":
            self.select_bottom()
        else:
            self.select_index(int(index))

    # ============================================================ #
    # Result handling
    # ============================================================ #

    search_forced = False
    def force_search(self):
        self.search_forced = True

    def should_search_again(self):
        return self.query != self.old_query or self.search_forced

    old_query = u""
    def do_search(self, query):
        with self.percol.global_lock:
            self.index = 0
            self.results = self.finder.get_results(query)
            self.marks   = {}
            # search finished
            self.search_forced = False
            self.old_query = query

    def get_result(self, index):
        try:
            return self.results[index][0]
        except IndexError:
            return None

    def get_selected_result(self):
        return self.get_result(self.index)

    def get_selected_results_with_index(self):
        results = self.get_marked_results_with_index()
        if not results:
            try:
                index = self.index
                result = self.results[index] # EAFP (results may be a zero-length list)
                results.append((result[0], index, result[2]))
            except Exception as e:
                debug.log("get_selected_results_with_index", e)
        return results

    # ------------------------------------------------------------ #
    #  Selections
    # ------------------------------------------------------------ #

    def select_index(self, idx):
        try:
            # For lazy results, correct "results_count" by getting
            # items (if available)
            self.results[idx]
            self.index = idx
        except:
            pass
        if self.results_count > 0:
            self.index = idx % self.results_count

    def select_top(self):
        self.select_index(0)

    def select_bottom(self):
        self.select_index(-1)

    # ------------------------------------------------------------ #
    # Mark
    # ------------------------------------------------------------ #

    def get_marked_results_with_index(self):
        if self.marks:
            return [(self.results[index][0], index, self.results[index][2])
                    for index in self.marks if self.get_is_marked(index)]
        else:
            return []

    def set_is_marked(self, marked, index = None):
        if index is None:
            index = self.index          # use current index
        self.marks[index] = marked

    def get_is_marked(self, index = None):
        if index is None:
            index = self.index          # use current index
        return self.marks.get(index, False)

    # ------------------------------------------------------------ #
    # Caret position
    # ------------------------------------------------------------ #

    def set_caret(self, caret):
        q_len = len(self.query)
        self.caret = max(min(caret, q_len), 0)

    # ------------------------------------------------------------ #
    # Text
    # ------------------------------------------------------------ #

    def __decode_char(self, ch):
        if six.PY2:
            return chr(ch).decode(self.percol.encoding)
        else:
            return str(bytearray([ch]), encoding=self.percol.encoding)

    def append_char_to_query(self, ch):
        self.query += self.__decode_char(ch)
        self.forward_char()

    def insert_char(self, ch):
        q = self.query
        c = self.caret
        self.query = q[:c] + self.__decode_char(ch) + q[c:]
        self.set_caret(c + 1)

    def insert_string(self, string):
        caret_pos  = self.caret + len(string)
        self.query = self.query[:self.caret] + string + self.query[self.caret:]
        self.caret = caret_pos

    # ------------------------------------------------------------ #
    # Finder
    # ------------------------------------------------------------ #

    def remake_finder(self, new_finder_class):
        self.finder = self.finder.clone_as(new_finder_class)
