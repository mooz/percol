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

import percol.info
__doc__     = info.__doc__
__version__ = info.__version__
__logo__    = info.__logo__

import sys
import signal
import curses
import threading
import six

from percol import debug, action

from percol.display import Display
from percol.finder  import FinderMultiQueryString
from percol.key     import KeyHandler
from percol.model   import SelectorModel
from percol.view    import SelectorView
from percol.command import SelectorCommand

class TerminateLoop(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class Percol(object):
    def __init__(self, descriptors = None, encoding = "utf-8",
                 finder = None, action_finder = None,
                 candidates = None, actions = None,
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
        if action_finder is None:
            action_finder = FinderMultiQueryString

        self.actions = actions

        # wraps candidates (iterator)
        from percol.lazyarray import LazyArray
        self.candidates = LazyArray(candidates or [])

        # create model
        self.model_candidate = SelectorModel(percol = self,
                                             collection = self.candidates,
                                             finder = finder,
                                             query = query, caret = caret, index = index)
        self.model_action = SelectorModel(percol = self,
                                          collection = [action.desc for action in actions],
                                          finder = action_finder)
        self.model = self.model_candidate

    def has_no_candidate(self):
        return not self.candidates.has_nth_value(0)

    def has_only_one_candidate(self):
        return self.candidates.has_nth_value(0) and not self.candidates.has_nth_value(1)

    def __enter__(self):
        # init curses and it's wrapper
        self.screen  = curses.initscr()
        self.display = Display(self.screen, self.encoding)

        # create keyhandler
        self.keyhandler = key.KeyHandler(self.screen)

        # create view
        self.view = SelectorView(percol = self)

        # create command
        self.command_candidate = SelectorCommand(self.model_candidate, self.view)
        self.command_action = SelectorCommand(self.model_action, self.view)

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
                        action.act([arg for arg, _, _ in self.args_for_action], self)
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

    @property
    def command(self):
        """
        Returns corresponding model wrapper which provides advanced commands
        """
        if self.model is self.model_action:
            return self.command_action
        else:
            return self.command_candidate

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

                if self.model.should_search_again():
                    # search again
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
                return e.value

    # ============================================================ #
    # Key Handling
    # ============================================================ #

    keymap = {
        "C-i"         : lambda percol: percol.switch_model(),
        # text
        "C-h"         : lambda percol: percol.command.delete_backward_char(),
        "<backspace>" : lambda percol: percol.command.delete_backward_char(),
        "C-w"         : lambda percol: percol.command.delete_backward_word(),
        "C-u"         : lambda percol: percol.command.clear_query(),
        "<dc>"        : lambda percol: percol.command.delete_forward_char(),
        # caret
        "<left>"      : lambda percol: percol.command.backward_char(),
        "<right>"     : lambda percol: percol.command.forward_char(),
        # line
        "<down>"      : lambda percol: percol.command.select_next(),
        "<up>"        : lambda percol: percol.command.select_previous(),
        # page
        "<npage>"     : lambda percol: percol.command.select_next_page(),
        "<ppage>"     : lambda percol: percol.command.select_previous_page(),
        # top / bottom
        "<home>"      : lambda percol: percol.command.select_top(),
        "<end>"       : lambda percol: percol.command.select_bottom(),
        # mark
        "C-SPC"       : lambda percol: percol.command.toggle_mark_and_next(),
        # finish
        "RET"         : lambda percol: percol.finish(), # Is RET never sent?
        "C-j"         : lambda percol: percol.finish(),
        "C-c"         : lambda percol: percol.cancel()
    }

    def import_keymap(self, keymap, reset = False):
        if reset:
            self.keymap = {}
        else:
            self.keymap = dict(self.keymap)
        for key, cmd in six.iteritems(keymap):
            self.keymap[key] = cmd

    # default
    last_key = None
    def handle_key(self, ch):
        if ch == curses.KEY_RESIZE:
            self.last_key = self.handle_resize(ch)
        elif ch != -1 and self.keyhandler.is_utf8_multibyte_key(ch):
            self.last_key = self.handle_utf8(ch)
        else:
            self.last_key = self.handle_normal_key(ch)

    def handle_resize(self, ch):
        self.display.update_screen_size()
        # XXX: trash -1 (it seems that resize key sends -1)
        self.keyhandler.get_key_for(self.screen.getch())
        return key.SPECIAL_KEYS[ch]

    def handle_utf8(self, ch):
        ukey = self.keyhandler.get_utf8_key_for(ch)
        self.model.insert_string(ukey)
        return ukey.encode(self.encoding)

    def handle_normal_key(self, ch):
        k = self.keyhandler.get_key_for(ch)
        if k in self.keymap:
            self.keymap[k](self)
        elif self.keyhandler.is_displayable_key(ch):
            self.model.insert_char(ch)
        return k

    # ------------------------------------------------------------ #
    # Finish / Cancel
    # ------------------------------------------------------------ #

    def finish(self):
        # save selected candidates and use them later (in execute_action)
        raise TerminateLoop(self.finish_with_exit_code())          # success

    def cancel(self):
        raise TerminateLoop(self.cancel_with_exit_code())          # failure

    def finish_with_exit_code(self):
        self.args_for_action = self.model_candidate.get_selected_results_with_index()
        return 0

    def cancel_with_exit_code(self):
        return 1
