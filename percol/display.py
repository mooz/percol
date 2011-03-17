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
    def __init__(self, screen):
        self.screen = screen
        curses.start_color()
        self.init_color_pairs()
        self.parser = markup.MarkupParser()

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

    def get_position_x(self, x_align, x_offset, whole_len):
        position = 0
        if x_align == "left":
            position = x_offset
        elif x_align == "right":
            position = self.WIDTH - whole_len - x_offset
        return position

    def get_position_y(self, y_align, y_offset):
        position = 0
        if y_align == "top":
            position = y_offset
        elif y_align == "bottom":
            position = self.HEIGHT - y_offset
        return position

    @property
    def WIDTH(self):
        return self.screen.getmaxyx()[1]

    @property
    def HEIGHT(self):
        return self.screen.getmaxyx()[0]

    def print_string(self, string,
                     y_align = "top", y_offset = 0,
                     x_align = "left", x_offset = 0):
        tokens = self.parser.parse(string)

        whole_len = reduce(lambda length, pair: length + len(pair[0]), tokens, 0)

        position_x = self.get_position_x(x_align, x_offset, whole_len)
        position_y = self.get_position_y(y_align, y_offset)

        for s, attrs in tokens:
            flag = self.get_color_pair(get_fg_color(attrs), get_bg_color(attrs))

            for attr in get_attributes(attrs):
                flag |= attr

            try:
                self.screen.addnstr(position_y, position_x, s, self.WIDTH - position_x, flag)
            except Exception as e:
                debug.log("Exception", e)

            position_x += len(s)

if __name__ == "__main__":
    screen = curses.initscr()
    display = Display(screen)
    display.print_string("f<underline>oooo<red>ba</underline>aa</red>baz", x_offset = 10)
    display.print_string("fo<on_green>ooo<red>ba<bold>a</on_green>a</bold></red>baz", x_align = "right", x_offset = 10)
    screen.getch()
