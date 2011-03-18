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
import types
import curses

import markup, debug

FG_COLORS = {
    "black"   : curses.COLOR_BLACK,
    "blue"    : curses.COLOR_BLUE,
    "cyan"    : curses.COLOR_CYAN,
    "green"   : curses.COLOR_GREEN,
    "magenta" : curses.COLOR_MAGENTA,
    "red"     : curses.COLOR_RED,
    "white"   : curses.COLOR_WHITE,
    "yellow"  : curses.COLOR_YELLOW,
}

BG_COLORS = dict(("on_" + name, value) for name, value in FG_COLORS.iteritems())

ATTRS = {
    "altcharset" : curses.A_ALTCHARSET,
    "blink"      : curses.A_BLINK,
    "bold"       : curses.A_BOLD,
    "dim"        : curses.A_DIM,
    "normal"     : curses.A_NORMAL,
    "standout"   : curses.A_STANDOUT,
    "underline"  : curses.A_UNDERLINE,
}

COLORS = len(FG_COLORS)

# ============================================================ #
# Markup
# ============================================================ #

def get_fg_color(attrs):
    for attr in attrs:
        if attr in FG_COLORS:
            return FG_COLORS[attr]
    return FG_COLORS["white"]

def get_bg_color(attrs):
    for attr in attrs:
        if attr in BG_COLORS:
            return BG_COLORS[attr]
    return BG_COLORS["on_black"]

def get_attributes(attrs):
    for attr in attrs:
        if attr in ATTRS:
            yield ATTRS[attr]

# ============================================================ #
# Display
# ============================================================ #

class Display(object):
    def __init__(self, screen, encoding):
        self.screen = screen
        self.encoding = encoding
        curses.start_color()
        self.init_color_pairs()
        self.parser = markup.MarkupParser()

    @property
    def WIDTH(self):
        return self.screen.getmaxyx()[1]

    @property
    def HEIGHT(self):
        return self.screen.getmaxyx()[0]

    # ============================================================ #
    # Color Pairs
    # ============================================================ #

    def init_color_pairs(self):
        for fg_s, fg in FG_COLORS.iteritems():
            for bg_s, bg in BG_COLORS.iteritems():
                if not (fg == bg == 0):
                    curses.init_pair(self.get_pair_number(fg, bg), fg, bg)

    def get_pair_number(self, fg, bg):
        return fg + bg * COLORS

    def get_color_pair(self, fg, bg):
        return curses.color_pair(self.get_pair_number(fg, bg))

    # ============================================================ #
    # Unicode
    # ============================================================ #

    def display_len(self, s, beg = None, end = None):
        if s.__class__ != types.UnicodeType:
            return len(s)

        if beg is None:
            beg = 0
        if end is None:
            end = len(s)

        dlen = end - beg
        for i in xrange(beg, end):
            if unicodedata.east_asian_width(s[i]) in ("W", "F"):
                dlen += 1

        return dlen

    # ============================================================ #
    # Aligned string
    # ============================================================ #

    def get_pos_x(self, x_align, x_offset, whole_len):
        position = 0

        if x_align == "left":
            position = x_offset
        elif x_align == "right":
            position = self.WIDTH - whole_len - x_offset
        elif x_align == "center":
            position = x_offset + (int(self.WIDTH - whole_len) / 2)

        return position

    def get_pos_y(self, y_align, y_offset):
        position = 0

        if y_align == "top":
            position = y_offset
        elif y_align == "bottom":
            position = self.HEIGHT - y_offset
        elif y_align == "center":
            position = y_offset + int(self.HEIGHT / 2)

        return position

    def get_flag_from_attrs(self, attrs):
        flag = self.get_color_pair(get_fg_color(attrs), get_bg_color(attrs))

        for attr in get_attributes(attrs):
            flag |= attr

        return flag

    def add_aligned_string_markup(self, markup,
                                  y_align = "top", x_align = "left",
                                  y_offset = 0, x_offset = 0,
                                  fill = False, fill_char = " ", fill_style = 0):
        tokens       = self.parser.parse(markup)
        display_lens = [self.display_len(s) for (s, attrs) in tokens]
        whole_len    = sum(display_lens)

        pos_x = self.get_pos_x(x_align, x_offset, whole_len)
        pos_y = self.get_pos_y(y_align, y_offset)

        org_pos_x = pos_x

        for i, (s, attrs) in enumerate(tokens):
            self.add_string(s, pos_y, pos_x, self.attrs_to_style(attrs), n = len(self.get_raw_string(s)))
            pos_x += display_lens[i]

        if fill:
            self.add_filling(fill_char, pos_y, 0, org_pos_x, fill_style)
            self.add_filling(fill_char, pos_y, pos_x, self.WIDTH, fill_style)

    def add_aligned_string(self, s,
                           y_align = "top", x_align = "left",
                           y_offset = 0, x_offset = 0,
                           style = 0,
                           fill = False, fill_char = " ", fill_style = None):
        display_len = self.display_len(s)

        pos_x = self.get_pos_x(x_align, x_offset, display_len)
        pos_y = self.get_pos_y(y_align, y_offset)

        self.add_string(s, pos_y, pos_x, style, n = len(self.get_raw_string(s)))

        if fill:
            if fill_style is None:
                fill_style = style
            self.add_filling(fill_char, pos_y, 0, pos_x, fill_style)
            self.add_filling(fill_char, pos_y, pos_x + display_len, self.WIDTH, fill_style)

    def add_filling(self, fill_char, pos_y, pos_x_beg, pos_x_end, style):
        filling_len = pos_x_end - pos_x_beg
        if filling_len > 0:
            self.add_string(fill_char * filling_len, pos_y, pos_x_beg, style)

    def attrs_to_style(self, attrs):
        style = self.get_color_pair(get_fg_color(attrs), get_bg_color(attrs))
        for attr in get_attributes(attrs):
            style |= attr
        return style

    def add_string(self, s, pos_y = 0, pos_x = 0, style = 0, n = -1):
        self.addnstr(pos_y, pos_x, s, n if n >= 0 else self.WIDTH - pos_x, style)

    # ============================================================ #
    # Fundamental
    # ============================================================ #

    def erase(self):
        self.screen.erase()

    def clear(self):
        self.screen.clear()

    def get_raw_string(self, s):
        return s.encode(self.encoding) if s.__class__ == types.UnicodeType else s

    def addnstr(self, y, x, s, n, style):
        try:
            self.screen.addnstr(y, x, self.get_raw_string(s), n, style)
            return True
        except curses.error:
            return False

if __name__ == "__main__":
    import locale

    locale.setlocale(locale.LC_ALL, '')

    screen = curses.initscr()

    display = Display(screen, locale.getpreferredencoding())

    display.add_string("-" * display.WIDTH, pos_y = 2)

    display.add_aligned_string_markup("<underline><bold><red>foo</red> <blue>bar</blue> <green>baz<green/> <cyan>qux</cyan></bold></underline>",
                                      x_align = "center", y_offset = 3)

    display.add_aligned_string_markup(u"ああ，<on_green>なんて<red>赤くて<bold>太くて</on_green>太い，</bold>そして赤い</red>リンゴ",
                                      y_offset = 4,
                                      x_offset = -20,
                                      x_align = "center",
                                      fill = True, fill_char = "*")

    display.add_aligned_string(u"こんにちは",
                               y_offset = 5,
                               x_offset = 0,
                               x_align = "right",
                               fill = True, fill_char = '*', fill_style = display.attrs_to_style(("bold", "white", "on_green")))

    display.add_aligned_string(u" foo bar baz qux ",
                               x_align = "center", y_align = "center",
                               style = display.attrs_to_style(("bold", "white", "on_magenta")),
                               fill = True, fill_char = '-')

    screen.getch()
