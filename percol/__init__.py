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

import key, debug, action, display, theme
from finder import FinderMultiQueryString, FinderMultiQueryRegex

class TerminateLoop(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

MODE_POWDER = 0
MODE_ACTION = 1
MODE_COUNT  = 2

class Percol(object):
    def __init__(self,
                 descriptors = None, collection = None,
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

        self.init_statuses(collection = collection,
                           actions = actions,
                           finder = (finder or FinderMultiQueryString))
        self.collection = collection
        self.actions    = actions
        self.setup_results()
        self.setup_index(index)

        self.query = query or u""
        self.setup_caret(caret)

    def setup_results(self):
        self.mode_index = MODE_ACTION
        self.do_search(u"")             # XXX: we need to arrange act_query?
        self.mode_index = MODE_POWDER
        self.do_search(self.query)

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

    # default
    args_for_action = None
    def execute_action(self):
        if self.selected_actions and self.args_for_action:
            for name, _, act_idx in self.selected_actions:
                try:
                    action = self.actions[act_idx]
                    if action:
                        action.act([arg for arg, _, _ in self.args_for_action])
                except:
                    pass

    # ============================================================ #
    # Pager attributes
    # ============================================================ #

    @property
    def RESULTS_DISPLAY_MAX(self):
        return self.display.HEIGHT - 1

    @property
    def page_number(self):
        return int(self.index / self.RESULTS_DISPLAY_MAX) + 1

    @property
    def total_page_number(self):
        return max(int(math.ceil(1.0 * self.results_count / self.RESULTS_DISPLAY_MAX)), 1)

    @property
    def absolute_index(self):
        return self.index

    @property
    def absolute_page_head(self):
        return self.RESULTS_DISPLAY_MAX * int(self.absolute_index / self.RESULTS_DISPLAY_MAX)

    @property
    def absolute_page_tail(self):
        return self.absolute_page_head + self.RESULTS_DISPLAY_MAX

    @property
    def results_count(self):
        return len(self.status["results"])

    # ============================================================ #
    # Statuses
    # ============================================================ #

    @contextmanager
    def preferred_mode(self, prefer_index):
        original_index = self.mode_index
        try:
            self.mode_index = prefer_index
            yield
        finally:
            self.mode_index = original_index

    def init_statuses(self, collection, actions, finder):
        self.statuses = [None] * 2
        self.statuses[MODE_POWDER] = self.create_status(finder(collection))
        self.statuses[MODE_ACTION] = self.create_status(finder([action.desc for action in actions]))

        self.define_accessors_for_status()

    # default
    mode_index = MODE_POWDER

    @property
    def status(self):
        return self.statuses[self.mode_index]

    def switch_mode(self):
        self.mode_index = (self.mode_index + 1) % MODE_COUNT

    def create_status(self, finder):
        return {
            "query"             : u"",
            "old_query"         : u"",
            "index"             : 0,
            "caret"             : 0,
            "marks"             : None,
            "results"           : None,
            "finder"            : finder,
        }

    def define_accessors_for_status(self):
        def create_property(k):
            def getter(self):
                return self.status[k]
            def setter(self, v):
                 self.status[k] = v
            return getter, setter

        for k in self.create_status(None):
            setattr(self.__class__, k, property(*create_property(k)))

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
    # Result handling
    # ============================================================ #

    def do_search(self, query):
        with self.global_lock:
            self.index = 0
            self.status["results"] = self.finder.get_results(query)
            self.status["marks"]   = [False] * self.results_count

    def get_result(self, index):
        try:
            return self.results[index][0]
        except IndexError:
            return None

    def get_selected_result(self):
        return self.get_result(self.index)

    def get_objective_results_for_status(self, status_idx):
        with self.preferred_mode(status_idx):
            results = self.get_marked_results_with_index()
            if not results:
                try:
                    index = self.index
                    result = self.results[index]
                    results.append((result[0], index, result[2]))
                except:
                    pass
        return results

    # ============================================================ #
    # Display
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
    # Prompt
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
    # Commands
    # ============================================================ #

    # ------------------------------------------------------------ #
    #  Selections
    # ------------------------------------------------------------ #

    def select_index(self, idx):
        if self.results_count > 0:
            self.index = idx % self.results_count

    def select_next(self):
        self.select_index(self.index + 1)

    def select_previous(self):
        self.select_index(self.index - 1)

    def select_next_page(self):
        self.select_index(self.index + self.RESULTS_DISPLAY_MAX)

    def select_previous_page(self):
        self.select_index(self.index - self.RESULTS_DISPLAY_MAX)

    def select_top(self):
        self.select_index(0)

    def select_bottom(self):
        self.select_index(self.results_count - 1)

    # ------------------------------------------------------------ #
    # Mark
    # ------------------------------------------------------------ #

    def get_marked_results_with_index(self):
        if self.marks:
            return [(self.results[i][0], i, self.results[i][2])
                    for i, marked in enumerate(self.marks) if marked]
        else:
            return []

    def toggle_mark(self):
        self.marks[self.index] ^= True

    def toggle_mark_and_next(self):
        self.toggle_mark()
        self.select_next()

    # ------------------------------------------------------------ #
    # Caret position
    # ------------------------------------------------------------ #

    def set_caret(self, caret):
        q_len = len(self.query)

        self.status["caret"] = max(min(caret, q_len), 0)

    def beginning_of_line(self):
        self.set_caret(0)

    def end_of_line(self):
        self.set_caret(len(self.query))

    def backward_char(self):
        self.set_caret(self.status["caret"] - 1)

    def forward_char(self):
        self.set_caret(self.status["caret"] + 1)

    # ------------------------------------------------------------ #
    # Text
    # ------------------------------------------------------------ #

    def append_char_to_query(self, ch):
        self.query += chr(ch).decode(self.encoding)
        self.forward_char()

    def insert_char(self, ch):
        q = self.query
        c = self.status["caret"]
        self.query = q[:c] + chr(ch).decode(self.encoding) + q[c:]
        self.set_caret(c + 1)

    def insert_string(self, string):
        caret_pos  = self.caret + len(string)
        self.query = self.query[:self.caret] + string + self.query[self.caret:]
        self.caret = caret_pos

    def delete_backward_char(self):
        if self.status["caret"] > 0:
            self.backward_char()
            self.delete_forward_char()

    def delete_forward_char(self):
        caret = self.status["caret"]
        self.query = self.query[:caret] + self.query[caret + 1:]

    def delete_end_of_line(self):
        self.query = self.query[:self.status["caret"]]

    def clear_query(self):
        self.query = u""

    # ------------------------------------------------------------ #
    # Text > kill
    # ------------------------------------------------------------ #

    def kill_end_of_line(self):
        self.killed = self.query[self.caret:]
        self.query  = self.query[:self.caret]

    killed = None                  # default
    def yank(self):
        if self.killed:
            self.insert_string(self.killed)

    # ------------------------------------------------------------ #
    # Finish / Cancel
    # ------------------------------------------------------------ #

    def finish(self):
        self.args_for_action = self.get_objective_results_for_status(MODE_POWDER)

        raise TerminateLoop("Finished")

    def cancel(self):
        raise TerminateLoop("Canceled")

    # ============================================================ #
    # Key Handling
    # ============================================================ #

    keymap = {
        "C-i"         : switch_mode,
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

    # ============================================================ #
    # Actions
    # ============================================================ #

    @property
    def selected_actions(self):
        return debug.dump(self.get_objective_results_for_status(MODE_ACTION))
