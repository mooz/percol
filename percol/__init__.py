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

import key, debug, action, display
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
    colors = {
        "normal_line"   : 1,
        "selected_line" : 2,
        "marked_line"   : 3,
        "keyword"       : 4,
    }

    def __init__(self,
                 descriptors = None, collection = None,
                 finder = None, actions = None,
                 encoding = "utf-8"):
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

        self.global_lock = threading.Lock()

    def __enter__(self):
        self.screen     = curses.initscr()
        self.keyhandler = key.KeyHandler(self.screen)

        curses.start_color()
        # foreground, background
        curses.init_pair(self.colors["normal_line"]     , curses.COLOR_WHITE,  curses.COLOR_BLACK)   # normal
        curses.init_pair(self.colors["selected_line"]   , curses.COLOR_WHITE,  curses.COLOR_MAGENTA) # line selected
        curses.init_pair(self.colors["marked_line"]     , curses.COLOR_BLACK,  curses.COLOR_CYAN)    # line marked
        curses.init_pair(self.colors["keyword"]         , curses.COLOR_YELLOW, curses.COLOR_BLACK)   # keyword

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

    def update_screen_size(self):
        self.HEIGHT, self.WIDTH = self.screen.getmaxyx()

    # ============================================================ #
    # Pager attributes
    # ============================================================ #

    @property
    def RESULTS_DISPLAY_MAX(self):
        return self.HEIGHT - 1

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

    @property
    def needed_count(self):
        return self.total_page_number * self.RESULTS_DISPLAY_MAX - self.results_count

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
            "results_generator" : None,
            "results_cache"     : {},
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
        self.init_display()

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

    def init_display(self):
        self.update_screen_size()
        # XXX: init results. ugly.
        self.mode_index = MODE_ACTION
        self.do_search(u"")
        self.mode_index = MODE_POWDER
        self.do_search(u"")

        self.refresh_display()

    # ============================================================ #
    # Result handling
    # ============================================================ #

    def do_search(self, query):
        with self.global_lock:
            self.index = 0

            if self.results_cache.has_key(query):
                self.status["results"], self.status["results_generator"] = self.results_cache[query]
                # we have to check the cache is complete or not
                needed_count = self.needed_count
                if needed_count > 0:
                    self.get_more_results(count = needed_count)
            else:
                self.status["results_generator"] = self.finder.find(query)
                self.status["results"] = [result for result
                                          in islice(self.status["results_generator"], self.RESULTS_DISPLAY_MAX)]
                # cache results and generator
                self.results_cache[query] = self.status["results"], self.status["results_generator"]

            self.status["marks"] = [False] * self.results_count

    def get_more_results(self, count = None):
        if count is None:
            count = self.RESULTS_DISPLAY_MAX

        results = [result for result in islice(self.status["results_generator"], count)]
        got_results_count = len(results)

        if got_results_count > 0:
            self.status["results"].extend(results)
            self.status["marks"].extend([False] * got_results_count)

        return got_results_count

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

    def addnstr(self, y, x, s, n, color):
        raw_s = s.encode(self.encoding) if s.__class__ == types.UnicodeType else s
        self.screen.addnstr(y, x, raw_s, self.WIDTH - x, color)

    def refresh_display(self):
        self.screen.erase()
        self.display_results()
        self.display_prompt()
        self.screen.refresh()

    def display_line(self, y, x, s, color = None):
        if color is None:
            color = curses.color_pair(self.colors["normal_line"])

        self.addnstr(y, x, s, self.WIDTH - x, color)

        # add padding
        s_len = display.display_len(s)
        padding_len = self.WIDTH - (x + s_len)
        if padding_len > 0:
            try:
                self.addnstr(y, x + s_len, " " * padding_len, padding_len, color)
            except curses.error as e:
                # XXX: sometimes, we get error
                pass

    def display_result(self, y, result, is_current = False, is_marked = False):
        line, find_info, abs_idx = result

        if is_current:
            line_style = curses.color_pair(self.colors["selected_line"])
        elif is_marked:
            line_style = curses.color_pair(self.colors["marked_line"])
        else:
            line_style = curses.color_pair(self.colors["normal_line"])

        keyword_style = curses.A_BOLD
        if is_current or is_marked:
            keyword_style |= line_style
        else:
            keyword_style |= curses.color_pair(self.colors["keyword"])

        self.display_line(y, 0, line, color = line_style)

        for (subq, match_info) in find_info:
            for x_offset, subq_len in match_info:
                try:
                    x_offset_real = display.display_len(line, 0, x_offset)
                    self.addnstr(y, x_offset_real,
                                 line[x_offset:x_offset + subq_len],
                                 self.WIDTH - x_offset_real,
                                 keyword_style)
                except curses.error as e:
                    debug.log("addnstr", str(e) + " ({0})".format(y))
                    pass

    def display_results(self):
        with self.global_lock:
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
        return 1                        # 0

    @property
    def PROMPT_OFFSET_V(self):
        return 0                        # self.RESULTS_DISPLAY_MAX

    PROMPT  = u"QUERY> %q"
    RPROMPT = u"(%i/%I) [%n/%N]"

    def display_prompt(self):
        # display underline
        style = curses.color_pair(self.colors["normal_line"]) | curses.A_UNDERLINE
        self.addnstr(self.PROMPT_OFFSET_V, 0, " " * self.WIDTH, self.WIDTH, style)

        caret_x = -1
        caret_y = -1

        try:
            rprompt = self.format_prompt_string(self.RPROMPT)
            self.addnstr(self.PROMPT_OFFSET_V, self.WIDTH - len(rprompt), rprompt, len(rprompt), style)
            # when %q is specified, record its position
            if self.last_query_position >= 0:
                caret_x = self.WIDTH - len(rprompt) + self.last_query_position
                caret_y = self.PROMPT_OFFSET_V
        except curses.error:
            pass

        try:
            prompt = self.format_prompt_string(self.PROMPT)
            self.addnstr(self.PROMPT_OFFSET_V, 0, prompt, self.WIDTH, style)
            # when %q is specified, record its position
            if self.last_query_position >= 0:
                caret_x = self.last_query_position
                caret_y = self.PROMPT_OFFSET_V
        except curses.error:
            pass

        try:
            # move caret
            if caret_x >= 0 and caret_y >= 0:
                self.screen.move(caret_y, caret_x + display.display_len(self.query, 0, self.caret))
        except curses.error:
            pass

    # default value
    last_query_position = -1
    def handle_format_prompt_query(self, matchobj):
        # -1 is from first '%' of %([a-zA-Z%])
        self.last_query_position = matchobj.start(1) - 1
        return self.query

    prompt_replacees = {
        "%" : lambda self, matchobj: "%",
        # display query and caret
        "q" : lambda self, matchobj: self.handle_format_prompt_query(matchobj),
        # display query but does not display caret
        "Q" : lambda self, matchobj: self.query,
        "n" : lambda self, matchobj: self.page_number,
        "N" : lambda self, matchobj: self.total_page_number,
        "i" : lambda self, matchobj: self.absolute_index + (1 if self.results_count > 0 else 0),
        "I" : lambda self, matchobj: self.results_count,
        "c" : lambda self, matchobj: self.status["caret"],
        "k" : lambda self, matchobj: self.last_key
    }

    def format_prompt_string(self, s):
        self.last_query_position = -1

        def formatter(matchobj):
            al = matchobj.group(1)
            if self.prompt_replacees.has_key(al):
                res = self.prompt_replacees[al](self, matchobj)
                return (res if res.__class__ == types.UnicodeType
                        else unicode(str(res), self.encoding, 'replace'))
            else:
                return u""

        return re.sub(r'%([a-zA-Z%])', formatter, s)

    # ============================================================ #
    # Commands
    # ============================================================ #

    # ------------------------------------------------------------ #
    #  Selections
    # ------------------------------------------------------------ #

    def select_index(self, idx):
        if idx >= self.results_count:
            self.get_more_results()

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
        # resize
        self.update_screen_size()

        # get results
        needed_count = self.needed_count
        if needed_count > 0:
            self.get_more_results(count = needed_count)

    # ============================================================ #
    # Actions
    # ============================================================ #

    @property
    def selected_actions(self):
        return debug.dump(self.get_objective_results_for_status(MODE_ACTION))
