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

import unicodedata

def display_len(s, beg = None, end = None):
    if beg is None:
        beg = 0
    if end is None:
        end = len(s)

    dlen = end - beg
    for i in xrange(beg, end):
        if unicodedata.east_asian_width(s[i]) in ("W", "F", "A"):
            dlen += 1
    return dlen
