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

class ModelPercol(object):
    def __init__(query = None, caret = None, index = None, finder = None):
        self.query = self.old_query = query or u""

        self.init_statuses(collection = collection,
                           actions = actions,
                           finder = (finder or FinderMultiQueryString))

        self.setup_results()
        self.setup_index(index)

        self.setup_caret()

    def setup_caret(self, caret):
        if isinstance(caret, types.StringType) or isinstance(caret, types.UnicodeType):
            try:
                caret = int(caret)
            except ValueError:
                caret = None
        if caret is None or caret < 0 or caret > display.display_len(self.query):
            caret = display.display_len(self.query)
        self.caret = caret

    def setup_index(self, index):
        if index is None or index == "first":
            self.select_top()
        elif index == "last":
            self.select_bottom()
        else:
            try:
                self.select_index(int(index))
            except:
                self.select_top()
