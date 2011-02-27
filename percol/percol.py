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

from itertools import islice

class TerminateLoop(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class Percol:
    def __init__(self, target):
        self.stdin  = target["stdin"]
        self.stdout = target["stdout"]
        self.stderr = target["stderr"]

        self.collection = self.stdin.read().split("\n")
        self.target = target

        self.output_buffer = []

    def __enter__(self):
        self.screen = curses.initscr()

        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_WHITE) # foreground, background
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK) # foreground, background

        # XXX: When we set signal.SIG_IGN to 2nd argument,
        # it seems that ^c key cannot be handled with getch.
        # signal.signal(signal.SIGINT, signal.SIG_IGN)
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

    def loop(self):
        scr = self.screen

        status = { "index"      : 0,
                   "rows "      : 0,
                   "results"    : None }

        CANDIDATES_MAX = 10

        def handle_special(s, ch):
            ENTER     = 10
            BACKSPACE = 127
            DELETE    = 126
            CTRL_A    = 1
            CTRL_B    = 2
            CTRL_C    = 3
            CTRL_D    = 4
            CTRL_H    = 8
            CTRL_N    = 14
            CTRL_P    = 16

            if ch in (BACKSPACE, CTRL_H):
                return s[:-1]
            elif ch == CTRL_A:
                return ""
            elif ch == CTRL_N:
                status["index"] = (status["index"] + 1) % status["rows"]
            elif ch == CTRL_P:
                status["index"] = (status["index"] - 1) % status["rows"]
            elif ch == ENTER:
                self.output("{0}\n".format(get_selected_candidate()))
                raise TerminateLoop("Bye!")
            elif ch < 0:
                raise TerminateLoop("Bye!")

            return s

        def log(name, s = ""):
            with open("/tmp/log", "a") as f:
                f.write(name + " :: " + str(s) + "\n")

        def get_selected_candidate():
            results = status["results"]
            index   = status["index"]

            try:
                return results[index][0]
            except IndexError:
                return ""

        def display_result(pos, result, is_current = False):
            line, pairs = result

            if is_current:
                scr.addstr(pos, 0, line, curses.color_pair(1))
            else:
                scr.addstr(pos, 0, line)

            for q, offsets in pairs:
                qlen = len(q)

                try:
                    for offset in offsets:
                        scr.addstr(pos, offset, line[offset:offset + qlen], curses.color_pair(2))
                except curses.error:
                    pass

        def display_results():
            voffset = 1
            for i, result in enumerate(status["results"]):
                display_result(i + voffset, result, is_current = i == status["index"])
            scr.refresh()

        def display_prompt(query):
            # display prompt
            prompt_str = "QUERY> " + query
            scr.addstr(0, 0, prompt_str)
            scr.move(0, len(prompt_str))

        def do_search(query):
            status["index"]   = 0
            status["results"] = [result for result in islice(self.search(query), CANDIDATES_MAX)]
            status["rows"]    = len(status["results"])

        def input_query():
            ch = scr.getch()
            scr.clear()

            try:
                if 32 <= ch <= 126:
                    q = query + chr(ch)
                else:
                    q = handle_special(query, ch)
            except ValueError:
                pass

            # DEBUG: display key code
            scr.addstr(0, 30, "<keycode: {0}>".format(ch))

            return q

        def refresh_display():
            display_results()
            display_prompt(query)
            scr.refresh()

        query     = ""
        old_query = query

        # init
        do_search(query)
        refresh_display()

        while True:
            try:
                query = input_query()

                if query != old_query:
                    do_search(query)
                    old_query = query

                refresh_display()
            except TerminateLoop:
                break

    def search(self, query):
        def find_all(needle, haystack):
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

        def and_find(queries, line):
            res = []

            for q in queries:
                if not q in line:
                    return None
                else:
                    res.append((q, find_all(q, line)))

            return res

        for line in self.collection:
            res = and_find(query.split(" "), line)

            if res:
                yield line, res
