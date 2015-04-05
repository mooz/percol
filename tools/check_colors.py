#!/usr/bin/env python

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
