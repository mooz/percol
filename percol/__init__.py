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

"""Adds flavor of interactive filtering to the traditional pipe concept of shell.
Try
 $ A | percol | B
and you can display the output of command A and filter it intaractively then pass them to command B.
Interface of percol is highly inspired by anything.el for Emacs."""

__version__ = "0.0.1"

import sys
import signal
import curses
import math
import re
import threading
import types

from contextlib import contextmanager
from itertools import islice

import key, debug, action, display, theme, model
from finder import FinderMultiQueryString, FinderMultiQueryRegex

class TerminateLoop(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class Percol(object):
    def __init__(self,
                 descriptors = None, candidates = None,
                 finder = None, actions = None,
                 encoding = "utf-8",
                 query = None,
                 caret = None,
                 index = None):
        self.global_lock = threading.Lock()
        self.encoding = encoding

        if descriptors is None:
            self.stdin  = sys.stdin
            self.stdout = sys.stdout
            self.stderr = sys.stderr
        else:
            self.stdin  = descriptors["stdin"]
            self.stdout = descriptors["stdout"]
            self.stderr = descriptors["stderr"]

        # create models
        self.model_candidate = Model(collection = candidates, finder = finder,
                                     query = query, caret = caret, index = index)
        self.model_action = Model(collection = actions, finder = finder)

        self.selected_model = self.model_candidate

    def __enter__(self):
        self.screen     = curses.initscr()
        self.display    = display.Display(self.screen, self.encoding)
        self.keyhandler = key.KeyHandler(self.screen)

        signal.signal(signal.SIGINT, lambda signum, frame: None)

        # handle special keys like <f1>, <down>, ...
        self.screen.keypad(True)

        curses.raw()
        curses.noecho()
        curses.cbreak()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        curses.endwin()
        self.execute_action()

    def execute_action(self):
        selected_candidates = self.model_candidate.selected_results
        selected_actions = self.model_action.selected_results

        if selected_candidates and selected_actions:
            for name, _, action_idx in selected_actions:
                try:
                    self.actions[action_idx].act([arg for arg, _, _ in selected_candidates])
                except:
                    pass

    # ============================================================ #
    # Main Loop
    # ============================================================ #

    SEARCH_DELAY = 0.05

    def loop(self):
        self.refresh_display()
        self.result_updating_timer = None

        def search_and_refresh_display():
            self.do_search(self.query)
            self.refresh_display()

        while True:
            try:
                self.handle_key(self.screen.getch())

                if self.query != self.old_query:
                    # search again
                    self.old_query = self.query

                    with self.global_lock:
                        # critical section
                        if not self.result_updating_timer is None:
                            # clear timer
                            self.result_updating_timer.cancel()
                            self.result_updating_timer = None

                        # with bounce
                        t = threading.Timer(self.SEARCH_DELAY, search_and_refresh_display)
                        self.result_updating_timer = t
                        t.start()

                self.refresh_display()
            except TerminateLoop as e:
                break

    # ============================================================ #
    # View :: Display
    # ============================================================ #

    def refresh_display(self):
        with self.global_lock:
            self.display.erase()
            self.display_results()
            self.display_prompt()
            self.display.refresh()

    def display_line(self, y, x, s, style = None):
        if style is None:
            style = theme.CANDIDATES_LINE_BASIC
        self.display.add_aligned_string(s, y_offset = y, x_offset = x, style = style, fill = True)

    def display_result(self, y, result, is_current = False, is_marked = False):
        line, find_info, abs_idx = result

        if is_current:
            line_style = theme.CANDIDATES_LINE_SELECTED
        elif is_marked:
            line_style = theme.CANDIDATES_LINE_MARKED
        else:
            line_style = theme.CANDIDATES_LINE_BASIC

        keyword_style = theme.CANDIDATES_LINE_QUERY + line_style

        self.display_line(y, 0, line, style = line_style)

        for (subq, match_info) in find_info:
            for x_offset, subq_len in match_info:
                try:
                    x_offset_real = display.display_len(line, beg = 0, end = x_offset)
                    self.display.add_string(line[x_offset:x_offset + subq_len],
                                            pos_y = y,
                                            pos_x = x_offset_real,
                                            style = keyword_style)
                except curses.error as e:
                    debug.log("addnstr", str(e) + " ({0})".format(y))
                    pass

    def display_results(self):
        voffset = self.RESULT_OFFSET_V

        abs_head = self.absolute_page_head
        abs_tail = self.absolute_page_tail

        for pos, result in islice(enumerate(self.results), abs_head, abs_tail):
            rel_pos = pos - abs_head
            try:
                self.display_result(rel_pos + voffset, result,
                                    is_current = pos == self.index,
                                    is_marked = self.status["marks"][pos])
            except curses.error as e:
                debug.log("display_results", str(e))

    # ============================================================ #
    # View :: Prompt
    # ============================================================ #

    @property
    def RESULT_OFFSET_V(self):
        return self.PROMPT_OFFSET_V + 1

    @property
    def PROMPT_OFFSET_V(self):
        return 0

    PROMPT  = u"QUERY> %q"
    RPROMPT = u"(%i/%I) [%n/%N]"

    def do_display_prompt(self, format,
                          y_offset = 0, x_offset = 0,
                          y_align = "top", x_align = "left"):
        parsed = self.display.parser.parse(format)
        offset = 0
        tokens = []

        self.last_query_position = -1

        for s, attrs in parsed:
            tokens.append((self.format_prompt_string(s, offset), attrs))
            offset += display.display_len(s)

        y, x = self.display.add_aligned_string_tokens(tokens,
                                                      y_offset = y_offset,
                                                      x_offset = x_offset,
                                                      y_align = y_align,
                                                      x_align = x_align)

        # when %q is specified, record its position
        if self.last_query_position >= 0:
            self.caret_x = self.last_query_position + x
            self.caret_y = self.PROMPT_OFFSET_V

    def display_prompt(self):
        self.caret_x = -1
        self.caret_y = -1

        self.do_display_prompt(self.RPROMPT,
                               y_offset = self.PROMPT_OFFSET_V,
                               x_align = "right")

        self.do_display_prompt(self.PROMPT,
                               y_offset = self.PROMPT_OFFSET_V)

        try:
            # move caret
            if self.caret_x >= 0 and self.caret_y >= 0:
                self.screen.move(self.caret_y,
                                 self.caret_x + display.display_len(self.query, 0, self.caret))
        except curses.error:
            pass

    def handle_format_prompt_query(self, matchobj, offset):
        # -1 is from first '%' of %([a-zA-Z%])
        self.last_query_position = matchobj.start(1) - 1 + offset
        return self.query

    prompt_replacees = {
        "%" : lambda self, **args: "%",
        # display query and caret
        "q" : lambda self, **args: self.handle_format_prompt_query(args["matchobj"], args["offset"]),
        # display query but does not display caret
        "Q" : lambda self, **args: self.query,
        "n" : lambda self, **args: self.page_number,
        "N" : lambda self, **args: self.total_page_number,
        "i" : lambda self, **args: self.absolute_index + (1 if self.results_count > 0 else 0),
        "I" : lambda self, **args: self.results_count,
        "c" : lambda self, **args: self.status["caret"],
        "k" : lambda self, **args: self.last_key
    }

    format_pattern = re.compile(ur'%([a-zA-Z%])')
    def format_prompt_string(self, s, offset = 0):
        def formatter(matchobj):
            al = matchobj.group(1)
            if self.prompt_replacees.has_key(al):
                res = self.prompt_replacees[al](self, matchobj = matchobj, offset = offset)
                return (res if res.__class__ == types.UnicodeType
                        else unicode(str(res), self.encoding, 'replace'))
            else:
                return u""

        return re.sub(self.format_pattern, formatter, s)

    # ============================================================ #
    # Controller :: Key Handling
    # ============================================================ #

    keymap = {
        "C-i"         : switch_model,
        # text
        "<backspace>" : delete_backward_char,
        "C-h"         : delete_backward_char,
        "C-d"         : delete_forward_char,
        "<dc>"        : delete_forward_char,
        "C-k"         : kill_end_of_line,
        "C-y"         : yank,
        # caret
        "C-a"         : beginning_of_line,
        "C-e"         : end_of_line,
        "C-b"         : backward_char,
        "<left>"      : backward_char,
        "C-f"         : forward_char,
        "<right>"     : forward_char,
        # line
        "C-n"         : select_next,
        "<down>"      : select_next,
        "C-p"         : select_previous,
        "<up>"        : select_previous,
        # page
        "C-v"         : select_next_page,
        "<npage>"     : select_next_page,
        "M-v"         : select_previous_page,
        "<ppage>"     : select_previous_page,
        # top / bottom
        "M-<"         : select_top,
        "<home>"      : select_top,
        "M->"         : select_bottom,
        "<end>"       : select_bottom,
        # mark
        "C-SPC"       : toggle_mark_and_next,
        # finish
        "RET"         : finish,
        "C-m"         : finish,       # XXX: C-m cannot be handled? (seems to be interpreted as C-j)
        "C-j"         : finish,
        # cancel
        "C-g"         : cancel,
        "C-c"         : cancel
    }

    # default
    last_key = None
    def handle_key(self, ch):
        self.last_key = None

        if ch == curses.KEY_RESIZE:
            self.handle_resize()
            key = "<RESIZE>"
            # XXX: trash -1 (it seems that resize key sends -1)
            debug.log("trashed", self.keyhandler.get_key_for(self.screen.getch()))
        elif ch != -1 and self.keyhandler.is_utf8_multibyte_key(ch):
            ukey = self.keyhandler.get_utf8_key_for(ch)
            key  = ukey.encode(self.encoding)
            self.insert_string(ukey)
        else:
            k = self.keyhandler.get_key_for(ch)

            if self.keymap.has_key(k):
                self.keymap[k](self)
            elif self.keyhandler.is_displayable_key(ch):
                self.insert_char(ch)
            key = k

        self.last_key = key

    def handle_resize(self):
        self.display.update_screen_size()

    def switch_model(self):
        if self.selected_model is self.model_action:
            self.selected_model = self.model_candidate
        else:
            self.selected_model = self.model_action

    def finish(self):
        self.finished = True
        raise TerminateLoop("Finished")

    def cancel(self):
        raise TerminateLoop("Canceled")

