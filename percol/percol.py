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

import sys
import signal
import curses
import math
import re

from itertools import islice

def log(name, s = ""):
    with open("/tmp/percol-log", "a") as f:
        f.write(name + " : " + str(s) + "\n")

class TerminateLoop(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class Percol:
    colors = {
        "normal_line"   : 1,
        "selected_line" : 2,
        "marked_line"   : 3,
        "keyword"       : 4,
    }

    RESULT_OFFSET_Y = 1

    def __init__(self, target):
        self.stdin  = target["stdin"]
        self.stdout = target["stdout"]
        self.stderr = target["stderr"]

        self.collection = self.stdin.read().split("\n")
        # self.collection = re.split("(?<!\\\\)\n", self.stdin.read())

        self.target = target

        self.output_buffer = []

    def __enter__(self):
        self.screen = curses.initscr()

        curses.start_color()
        # foreground, background
        curses.init_pair(self.colors["normal_line"]     , curses.COLOR_WHITE,  curses.COLOR_BLACK)   # normal
        curses.init_pair(self.colors["selected_line"]   , curses.COLOR_WHITE,  curses.COLOR_MAGENTA) # line selected
        curses.init_pair(self.colors["marked_line"]     , curses.COLOR_BLACK,  curses.COLOR_CYAN)    # line marked
        curses.init_pair(self.colors["keyword"]         , curses.COLOR_YELLOW, curses.COLOR_BLACK)   # keyword

        signal.signal(signal.SIGINT, lambda signum, frame: None)

        curses.noecho()
        curses.cbreak()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        curses.endwin()

        if self.stdout:
            self.stdout.write("".join(self.output_buffer))

    def output(self, s):
        # delay actual output (wait curses to finish)
        self.output_buffer.append(s)

    def update_screen_size(self):
        self.HEIGHT, self.WIDTH = self.screen.getmaxyx()

    @property
    def RESULTS_DISPLAY_MAX(self):
        return self.HEIGHT - 1

    @property
    def page_number(self):
        return int(self.status["index"] / self.RESULTS_DISPLAY_MAX) + 1

    @property
    def total_page_number(self):
        return max(int(math.ceil(1.0 * self.results_count / self.RESULTS_DISPLAY_MAX)), 1)

    @property
    def absolute_index(self):
        return self.status["index"]

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

    def init_display(self):
        self.update_screen_size()
        self.do_search("")
        self.refresh_display()

    def loop(self):
        self.status = {
            "index"             : 0,
            "marks"             : None,
            "query"             : None,
            # result
            "results"           : None,
            "results_generator" : None,
        }

        self.results_cache = {}

        old_query = self.status["query"] = ""

        self.init_display()

        while True:
            try:
                self.handle_key(self.screen.getch())

                query = self.status["query"]

                if query != old_query:
                    self.do_search(query)
                    old_query = query

                self.refresh_display()
            except TerminateLoop as e:
                break

    def do_search(self, query):
        self.status["index"] = 0

        if self.results_cache.has_key(query):
            self.status["results"], self.status["results_generator"] = self.results_cache[query]
            # we have to check the cache is complete or not
            needed_count = self.needed_count
            if needed_count > 0:
                self.get_more_results(count = needed_count)
        else:
            self.status["results_generator"] = self.search(query)
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

    def refresh_display(self):
        self.screen.erase()
        self.display_results()
        self.display_prompt()
        self.screen.refresh()

    def get_result(self, index):
        results = self.status["results"]

        try:
            return results[index][0]
        except IndexError:
            return None

    def get_selected_result(self):
        return self.get_result(self.status["index"])

    def display_line(self, y, x, s, color = None):
        if color is None:
            color = curses.color_pair(self.colors["normal_line"])

        self.screen.addnstr(y, x, s, self.WIDTH - x, color)

        # add padding
        s_len = len(s)
        padding_len = self.WIDTH - (x + s_len)
        if padding_len > 0:
            try:
                self.screen.addnstr(y, x + s_len, " " * padding_len, padding_len, color)
            except curses.error as e:
                # XXX: sometimes, we get error
                pass

    def display_result(self, y, result, is_current = False, is_marked = False):
        line, pairs = result

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

        for q, x_offsets in pairs:
            q_len = len(q)
            for x_offset in x_offsets:
                try:
                    self.screen.addnstr(y, x_offset,
                                        line[x_offset:x_offset + q_len],
                                        self.WIDTH - x_offset,
                                        keyword_style)
                except curses.error as e:
                    log("addnstr", str(e) + " ({0})".format(y))
                    pass

    def display_results(self):
        voffset = self.RESULT_OFFSET_Y

        abs_head = self.absolute_page_head
        abs_tail = self.absolute_page_tail

        for pos, result in islice(enumerate(self.status["results"]), abs_head, abs_tail):
            rel_pos = pos - abs_head
            try:
                self.display_result(rel_pos + voffset, result,
                                    is_current = pos == self.status["index"],
                                    is_marked = self.status["marks"][pos])
            except curses.error as e:
                log("display_results", str(e))

    def display_prompt(self, query = None):
        if query is None:
            query = self.status["query"]

        # display prompt
        try:
            prompt_str = "QUERY> " + query
            self.screen.addnstr(0, 0, prompt_str, self.WIDTH)
        except curses.error:
            pass

        # display page number
        rprompt = "[{0}/{1}]".format(self.page_number, self.total_page_number)
        self.screen.addnstr(0, self.WIDTH - len(rprompt), rprompt, len(rprompt))

        # move caret to the prompt
        self.screen.move(0, len(prompt_str))

    def select_index(self, idx):
        if idx >= self.results_count:
            self.get_more_results()

        self.status["index"] = idx % self.results_count

    def handle_special(self, s, ch):
        ENTER     = 10
        BACKSPACE = 127
        DELETE    = 126
        CTRL_SPC  = 0
        CTRL_A    = 1
        CTRL_B    = 2
        CTRL_C    = 3
        CTRL_D    = 4
        CTRL_H    = 8
        CTRL_N    = 14
        CTRL_P    = 16

        def select_next():
            if self.status["index"] + 1 >= self.results_count:
                self.get_more_results()
            self.status["index"] = (self.status["index"] + 1) % self.results_count

        def select_previous():
            self.status["index"] = (self.status["index"] - 1) % self.results_count

        def toggle_mark():
            self.status["marks"][self.status["index"]] ^= True

        def finish():
            any_marked = False

            # TODO: make this action customizable
            def execute_action(arg):
                self.output("{0}\n".format(arg))

            for i, marked in enumerate(self.status["marks"]):
                if marked:
                    any_marked = True
                    execute_action(self.get_result(i))

            if not any_marked:
                execute_action(self.get_selected_result())

        # TODO: make keymap
        if ch in (BACKSPACE, CTRL_H):
            s = s[:-1]
        elif ch == CTRL_A:
            s = ""
        elif ch == CTRL_N:
            select_next()
        elif ch == CTRL_P:
            select_previous()
        elif ch == CTRL_SPC:
            # mark
            toggle_mark()
            select_next()
        elif ch == ENTER:
            finish()
            raise TerminateLoop("Finished")
        elif ch < 0:
            raise TerminateLoop("Canceled")

        return s

    def handle_key(self, ch):
        try:
            if 32 <= ch <= 126:
                self.status["query"] += chr(ch)
            elif ch == curses.KEY_RESIZE:
                self.handle_resize()
            else:
                self.status["query"] = self.handle_special(self.status["query"], ch)
        except ValueError:
            pass

        # DEBUG: display key code
        self.screen.addnstr(0, 30, "<keycode: {0}>".format(ch), self.WIDTH)

    def handle_resize(self):
        # resize
        self.update_screen_size()

        # get results
        needed_count = self.needed_count
        if needed_count > 0:
            self.get_more_results(count = needed_count)

    # ============================================================ #
    # Find
    # ============================================================ #

    def find_all(self, needle, haystack):
        stride = len(needle)

        if stride == 0:
            return [0]

        start  = 0
        res    = []

        while True:
            found = haystack.find(needle, start)
            if found < 0:
                break
            res.append(found)
            start = found + stride

        return res

    def and_find(self, queries, line):
        res = []

        for q in queries:
            if not q in line:
                return None
            else:
                res.append((q, self.find_all(q, line)))

        return res

    def search(self, query):
        for line in self.collection:
            res = self.and_find(query.split(" "), line)

            if res:
                yield line, res
