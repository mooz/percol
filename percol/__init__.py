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
import threading

import debug, action

from display import Display
from finder  import FinderMultiQueryString, FinderMultiQueryRegex
from key     import KeyHandler
from model   import SelectorModel
from view    import SelectorView

class TerminateLoop(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class Percol(object):
    def __init__(self, descriptors = None, encoding = "utf-8",
                 finder = None, candidates = None, actions = None,
                 query = None, caret = None, index = None):
        # initialization
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

        if finder is None:
            finder = FinderMultiQueryString

        self.actions = actions

        # create models
        self.model_candidate = SelectorModel(percol = self,
                                             collection = candidates, finder = finder,
                                             query = query, caret = caret, index = index)
        self.model_action = SelectorModel(percol = self,
                                          collection = [action.desc for action in actions],
                                          finder = finder)

        # set current model
        self.model = self.model_candidate

    def __enter__(self):
        # init curses and it's wrapper
        self.screen  = curses.initscr()
        self.display = Display(self.screen, self.encoding)

        # create keyhandler
        self.keyhandler = key.KeyHandler(self.screen)

        # create view
        self.view = SelectorView(percol = self)

        # suppress SIGINT termination
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

    args_for_action = None
    def execute_action(self):
        selected_actions = self.model_action.get_selected_results_with_index()

        if selected_actions and self.args_for_action:
            for name, _, act_idx in selected_actions:
                try:
                    action = self.actions[act_idx]
                    if action:
                        action.act([arg for arg, _, _ in self.args_for_action])
                except Exception as e:
                    debug.log("execute_action", e)

    # ============================================================ #
    # Statuses
    # ============================================================ #

    @property
    def opposite_model(self):
        """
        Returns opposite model for self.model
        """
        if self.model is self.model_action:
            return self.model_candidate
        else:
            return self.model_action

    def switch_model(self):
        self.model = self.opposite_model

    # ============================================================ #
    # Main Loop
    # ============================================================ #

    SEARCH_DELAY = 0.05

    def loop(self):
        self.view.refresh_display()
        self.result_updating_timer = None

        def search_and_refresh_display():
            self.model.do_search(self.model.query)
            self.view.refresh_display()

        while True:
            try:
                self.handle_key(self.screen.getch())

                if self.model.query != self.model.old_query:
                    # search again
                    self.model.old_query = self.model.query

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

                self.view.refresh_display()
            except TerminateLoop as e:
                break

    # ============================================================ #
    # Key Handling
    # ============================================================ #

    def select_next_page(self):
        self.model.select_index(self.model.index + self.view.RESULTS_DISPLAY_MAX)

    def select_previous_page(self):
        self.model.select_index(self.model.index - self.view.RESULTS_DISPLAY_MAX)

    keymap = {
        "C-i"         : lambda percol: percol.switch_model(),
        # text
        "<backspace>" : lambda percol: percol.model.delete_backward_char(),
        "<dc>"        : lambda percol: percol.model.delete_forward_char(),
        # caret
        "<left>"      : lambda percol: percol.model.backward_char(),
        "<right>"     : lambda percol: percol.model.forward_char(),
        # line
        "<down>"      : lambda percol: percol.model.select_next(),
        "<up>"        : lambda percol: percol.model.select_previous(),
        # page
        "<npage>"     : lambda percol: percol.select_next_page(),
        "<ppage>"     : lambda percol: percol.select_previous_page(),
        # top / bottom
        "<home>"      : lambda percol: percol.model.select_top(),
        "<end>"       : lambda percol: percol.model.select_bottom(),
        # mark
        "C-SPC"       : lambda percol: percol.model.toggle_mark_and_next(),
        # finish
        "RET"         : lambda percol: percol.finish(),
        "C-c"         : lambda percol: percol.cancel()
    }

    def import_keymap(self, keymap, reset = False):
        if reset:
            self.keymap = {}
        else:
            self.keymap = dict(self.keymap)
        for key, cmd in keymap.iteritems():
            self.keymap[key] = cmd

    # default
    last_key = None
    def handle_key(self, ch):
        self.last_key = None

        if ch == curses.KEY_RESIZE:
            self.handle_resize()
            key = "<RESIZE>"
            # XXX: trash -1 (it seems that resize key sends -1)
            self.keyhandler.get_key_for(self.screen.getch())
        elif ch != -1 and self.keyhandler.is_utf8_multibyte_key(ch):
            ukey = self.keyhandler.get_utf8_key_for(ch)
            key  = ukey.encode(self.encoding)
            self.model.insert_string(ukey)
        else:
            k = self.keyhandler.get_key_for(ch)

            if self.keymap.has_key(k):
                self.keymap[k](self)
            elif self.keyhandler.is_displayable_key(ch):
                self.model.insert_char(ch)
            key = k

        self.last_key = key

    def handle_resize(self):
        self.display.update_screen_size()

    # ------------------------------------------------------------ #
    # Finish / Cancel
    # ------------------------------------------------------------ #

    def finish(self):
        # save selected candidates and use them later (in execute_action)
        self.args_for_action = self.model_candidate.get_selected_results_with_index()
        raise TerminateLoop("Finished")

    def cancel(self):
        raise TerminateLoop("Canceled")
