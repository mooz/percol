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
import six
import curses
import re

from percol import markup, debug

FG_COLORS = {
    "black"   : curses.COLOR_BLACK,
    "red"     : curses.COLOR_RED,
    "green"   : curses.COLOR_GREEN,
    "yellow"  : curses.COLOR_YELLOW,
    "blue"    : curses.COLOR_BLUE,
    "magenta" : curses.COLOR_MAGENTA,
    "cyan"    : curses.COLOR_CYAN,
    "white"   : curses.COLOR_WHITE,
}

BG_COLORS = dict(("on_" + name, value) for name, value in six.iteritems(FG_COLORS))

ATTRS = {
    "altcharset" : curses.A_ALTCHARSET,
    "blink"      : curses.A_BLINK,
    "bold"       : curses.A_BOLD,
    "dim"        : curses.A_DIM,
    "normal"     : curses.A_NORMAL,
    "standout"   : curses.A_STANDOUT,
    "underline"  : curses.A_UNDERLINE,
    "reverse"    : curses.A_REVERSE,
}

COLOR_COUNT = len(FG_COLORS)

# ============================================================ #
# Markup
# ============================================================ #

def get_fg_color(attrs):
    for attr in attrs:
        if attr in FG_COLORS:
            return FG_COLORS[attr]
    return FG_COLORS["default"]

def get_bg_color(attrs):
    for attr in attrs:
        if attr in BG_COLORS:
            return BG_COLORS[attr]
    return BG_COLORS["on_default"]

def get_attributes(attrs):
    for attr in attrs:
        if attr in ATTRS:
            yield ATTRS[attr]

# ============================================================ #
# Unicode
# ============================================================ #

def screen_len(s, beg = None, end = None):
    if beg is None:
        beg = 0
    if end is None:
        end = len(s)

    if "\t" in s:
        # consider tabstop (very naive approach)
        beg = len(s[0:beg].expandtabs())
        end = len(s[beg:end].expandtabs())
        s = s.expandtabs()

    if not isinstance(s, six.text_type):
        return end - beg

    dis_len = end - beg
    for i in six.moves.range(beg, end):
        if unicodedata.east_asian_width(s[i]) in ("W", "F"):
            dis_len += 1

    return dis_len

def screen_length_to_bytes_count(string, screen_length_limit, encoding):
    bytes_count = 0
    screen_length = 0
    for unicode_char in string:
        screen_length += screen_len(unicode_char)
        char_bytes_count = len(unicode_char.encode(encoding))
        bytes_count += char_bytes_count
        if screen_length > screen_length_limit:
            bytes_count -= char_bytes_count
            break
    return bytes_count

# ============================================================ #
# Display
# ============================================================ #

class Display(object):
    def __init__(self, screen, encoding):
        self.screen   = screen
        self.encoding = encoding
        self.markup_parser   = markup.MarkupParser()

        curses.start_color()

        self.has_default_colors = curses.COLORS > COLOR_COUNT

        if self.has_default_colors:
            # xterm-256color
            curses.use_default_colors()
            FG_COLORS["default"]    = -1
            BG_COLORS["on_default"] = -1
            self.init_color_pairs()
        elif curses.COLORS != 0:
            # ansi linux rxvt ...etc.
            self.init_color_pairs()
            FG_COLORS["default"]    = curses.COLOR_WHITE
            BG_COLORS["on_default"] = curses.COLOR_BLACK
        else: # monochrome, curses.COLORS == 0
            # vt100 x10term wy520 ...etc.
            FG_COLORS["default"]    = curses.COLOR_WHITE
            BG_COLORS["on_default"] = curses.COLOR_BLACK

        self.update_screen_size()

    def update_screen_size(self):
        self.HEIGHT, self.WIDTH = self.screen.getmaxyx()

    @property
    def Y_BEGIN(self):
        return 0

    @property
    def Y_END(self):
        return self.HEIGHT - 1

    @property
    def X_BEGIN(self):
        return 0

    @property
    def X_END(self):
        return self.WIDTH - 1

    # ============================================================ #
    # Color Pairs
    # ============================================================ #

    def init_color_pairs(self):
        for fg_s, fg in six.iteritems(FG_COLORS):
            for bg_s, bg in six.iteritems(BG_COLORS):
                if not (fg == bg == 0):
                    curses.init_pair(self.get_pair_number(fg, bg), fg, bg)

    def get_normalized_number(self, number):
        return COLOR_COUNT if number < 0 else number

    def get_pair_number(self, fg, bg):
        if self.has_default_colors:
            # Assume the number of colors is up to 16 (2^4 = 16)
            return self.get_normalized_number(fg) | (self.get_normalized_number(bg) << 4)
        else:
            return self.get_normalized_number(fg) + self.get_normalized_number(bg) * COLOR_COUNT

    def get_color_pair(self, fg, bg):
        return curses.color_pair(self.get_pair_number(fg, bg))

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

    def add_aligned_string_markup(self, markup, **keywords):
        return self.add_aligned_string_tokens(self.markup_parser.parse(markup), **keywords)

    def add_aligned_string_tokens(self, tokens,
                                  y_align = "top", x_align = "left",
                                  y_offset = 0, x_offset = 0,
                                  fill = False, fill_char = " ", fill_style = None):
        dis_lens  = [screen_len(s) for (s, attrs) in tokens]
        whole_len = sum(dis_lens)

        pos_x = self.get_pos_x(x_align, x_offset, whole_len)
        pos_y = self.get_pos_y(y_align, y_offset)

        org_pos_x = pos_x

        for i, (s, attrs) in enumerate(tokens):
            self.add_string(s, pos_y, pos_x, self.attrs_to_style(attrs))
            pos_x += dis_lens[i]

        if fill:
            self.add_filling(fill_char, pos_y, 0, org_pos_x, fill_style)
            self.add_filling(fill_char, pos_y, pos_x, self.WIDTH, fill_style)

        return pos_y, org_pos_x

    def add_aligned_string(self, s,
                           y_align = "top", x_align = "left",
                           y_offset = 0, x_offset = 0,
                           style = None,
                           fill = False, fill_char = " ", fill_style = None):
        dis_len = screen_len(s)

        pos_x = self.get_pos_x(x_align, x_offset, dis_len)
        pos_y = self.get_pos_y(y_align, y_offset)

        self.add_string(s, pos_y, pos_x, style)

        if fill:
            if fill_style is None:
                fill_style = style
            self.add_filling(fill_char, pos_y, 0, pos_x, fill_style)
            self.add_filling(fill_char, pos_y, pos_x + dis_len, self.WIDTH, fill_style)

        return pos_y, pos_x

    def add_filling(self, fill_char, pos_y, pos_x_beg, pos_x_end, style):
        filling_len = pos_x_end - pos_x_beg
        if filling_len > 0:
            self.add_string(fill_char * filling_len, pos_y, pos_x_beg, style)

    def attrs_to_style(self, attrs):
        if attrs is None:
            return 0

        style = self.get_color_pair(get_fg_color(attrs), get_bg_color(attrs))
        for attr in get_attributes(attrs):
            style |= attr

        return style

    def add_string(self, s, pos_y = 0, pos_x = 0, style = None, n = -1):
        self.addnstr(pos_y, pos_x, s, n if n >= 0 else self.WIDTH - pos_x, style)

    # ============================================================ #
    # Fundamental
    # ============================================================ #

    def erase(self):
        self.screen.erase()

    def clear(self):
        self.screen.clear()

    def refresh(self):
        self.screen.refresh()

    def get_raw_string(self, s):
        return s.encode(self.encoding) if isinstance(s, six.text_type) else s

    def addnstr(self, y, x, s, n, style):
        if not isinstance(style, six.integer_types):
            style = self.attrs_to_style(style)

        # Compute bytes count of the substring that fits in the screen
        bytes_count_to_display = screen_length_to_bytes_count(s, n, self.encoding)

        try:
            sanitized_str = re.sub(r'[\x00-\x08\x0a-\x1f]', '?', s)
            raw_str = self.get_raw_string(sanitized_str)
            self.screen.addnstr(y, x, raw_str, bytes_count_to_display, style)
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
                               style = display.attrs_to_style(("bold", "white", "on_default")),
                               fill = True, fill_char = '-')

    screen.getch()
