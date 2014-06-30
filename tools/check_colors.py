#!/usr/bin/env python

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

import curses
import six

if __name__ == "__main__":
    screen = curses.initscr()

    try:
        curses.start_color()

        def get_fg_bg():
            for bg in six.moves.range(0, curses.COLORS):
                for fg in six.moves.range(0, curses.COLORS):
                    yield bg, fg

        def pair_number(fg, bg):
            return fg + bg * curses.COLORS

        def init_pairs():
            for bg, fg in get_fg_bg():
                if not (fg == bg == 0):
                    curses.init_pair(pair_number(fg, bg), fg, bg)

        def print_pairs(attrs = None, offset_y = 0):
            fmt = " ({0}:{1}) "
            fmt_len = len(fmt)

            for bg, fg in get_fg_bg():
                try:
                    color = curses.color_pair(pair_number(fg, bg))
                    if not attrs is None:
                        for attr in attrs:
                            color |= attr
                    screen.addstr(offset_y + bg, fg * fmt_len, fmt.format(fg, bg), color)
                    pass
                except curses.error:
                    pass

        def wait_input():
            screen.getch()

        init_pairs()
        print_pairs()
        print_pairs([curses.A_BOLD], offset_y = curses.COLORS + 1)
        screen.refresh()
        wait_input()
    finally:
        curses.endwin()
