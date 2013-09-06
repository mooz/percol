# -*- coding: utf-8 -*-
#
# Copyright (C) 2013 mooz
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
import os
import locale

from optparse import OptionParser

import percol
from percol import Percol
from percol import tty
from percol import debug
from percol import ansi

INSTRUCTION_TEXT = ansi.markup("""<bold><blue>{logo}</blue></bold>
                                <on_blue><underline> {version} </underline></on_blue>

You did not give any inputs to <underline>percol</underline>. Check following typical usages and try again.

<underline>(1) Giving a filename,</underline>

 $ <underline>percol</underline> /var/log/syslog

<underline>(2) or specifying a redirection.</underline>

 $ ps aux | <underline>percol</underline>

""").format(logo = percol.__logo__,
            version = percol.__version__)

def load_rc(percol, path = None, encoding = 'utf-8'):
    if path is None:
        path = os.path.expanduser("~/.percol.d/rc.py")
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rc.py')
    try:
        with open(path, 'r') as rc:
            exec(rc.read().decode(encoding), locals())
    except Exception as e:
        debug.log("Exception in rc file {0}".format(path), e)

def eval_string(percol, string_to_eval, encoding = 'utf-8'):
    try:
        import types
        if string_to_eval.__class__ != types.UnicodeType:
            string_to_eval = string_to_eval.decode(encoding)
        exec(string_to_eval, locals())
    except Exception as e:
        debug.log("Exception in eval_string", e)

def setup_options(parser):
    parser.add_option("--tty", dest = "tty",
                      help = "path to the TTY (usually, the value of $TTY)")
    parser.add_option("--rcfile", dest = "rcfile",
                      help = "path to the settings file")
    parser.add_option("--output-encoding", dest = "output_encoding",
                      help = "encoding for output")
    parser.add_option("--input-encoding", dest = "input_encoding", default = "utf8",
                      help = "encoding for input and output (default 'utf8')")
    parser.add_option("--query", dest = "query",
                      help = "pre-input query")
    parser.add_option("--eager", action = "store_true", dest = "eager", default = False,
                      help = "suppress lazy matching (slower, but display correct candidates count)")
    parser.add_option("--eval", dest = "string_to_eval",
                      help = "eval given string after loading the rc file")
    parser.add_option("--match-method", dest = "match_method", default = "",
                      help = "specify matching method for query. `string` (default) and `regex` are currently supported")
    parser.add_option("--caret-position", dest = "caret",
                      help = "position of the caret (default length of the `query`)")
    parser.add_option("--initial-index", dest = "index",
                      help = "position of the initial index of the selection (numeric, \"first\" or \"last\")")
    parser.add_option("--case-sensitive", dest = "case_sensitive", default = False, action="store_true",
                      help = "whether distinguish the case of query or not")
    parser.add_option("--reverse", dest = "reverse", default = False, action="store_true",
                      help = "whether reverse the order of candidates or not")
    parser.add_option("--auto-fail", dest = "auto_fail", default = False, action="store_true",
                      help = "auto fail if no candidates")
    parser.add_option("--auto-match", dest = "auto_match", default = False, action="store_true",
                      help = "auto matching if only one candidate")

    parser.add_option("--prompt-top", dest = "prompt_on_top", default = None, action="store_true",
                      help = "display prompt top of the screen (default)")
    parser.add_option("--prompt-bottom", dest = "prompt_on_top", default = None, action="store_false",
                      help = "display prompt bottom of the screen")
    parser.add_option("--result-top-down", dest = "results_top_down", default = None, action="store_true",
                      help = "display results top down (default)")
    parser.add_option("--result-bottom-up", dest = "results_top_down", default = None, action="store_false",
                      help = "display results bottom up instead of top down")

    parser.add_option("--quote", dest = "quote", default = False, action="store_true",
                      help = "whether quote the output line")
    parser.add_option("--peep", action = "store_true", dest = "peep", default = False,
                      help = "exit immediately with doing nothing to cache module files and speed up start-up time")

def set_proper_locale(options):
    locale.setlocale(locale.LC_ALL, '')
    output_encoding = locale.getpreferredencoding()
    if options.output_encoding:
        output_encoding = options.output_encoding
    return output_encoding

def read_input(filename, encoding, reverse=False):
    if filename:
        stream = open(filename, "r")
    else:
        stream = sys.stdin
    if reverse:
        lines = reversed(stream.readlines())
    else:
        lines = stream
    for line in lines:
        yield unicode(line.rstrip("\r\n"), encoding, "replace")
    stream.close()

def decide_match_method(options):
    if options.match_method == "regex":
        from percol.finder import FinderMultiQueryRegex
        return FinderMultiQueryRegex
    if options.match_method == "migemo":
        from percol.finder import FinderMultiQueryMigemo
        return FinderMultiQueryMigemo
    else:
        from percol.finder import FinderMultiQueryString
        return FinderMultiQueryString

def main():
    parser = OptionParser(usage = "Usage: %prog [options] [FILE]")
    setup_options(parser)
    options, args = parser.parse_args()

    if options.peep:
        exit(1)

    def exit_program(msg = None, show_help = True):
        if not msg is None:
            print("\n" + msg + "\n")
        if show_help:
            parser.print_help()
        exit(1)

    # get ttyname
    ttyname = options.tty or tty.get_ttyname()
    if not ttyname:
        exit_program("""Error: No tty name is given and failed to guess it from descriptors.
Maybe all descriptors are redirecred.""")

    # decide which encoding to use
    output_encoding = set_proper_locale(options)
    input_encoding = options.input_encoding

    with open(ttyname, "r+w") as tty_f:
        if not tty_f.isatty():
            exit_program("Error: {0} is not a tty file".format(ttyname), show_help = False)

        filename = args[0] if len(args) > 0 else None

        if filename is None and sys.stdin.isatty():
            tty_f.write(INSTRUCTION_TEXT)
            exit_program(show_help = False)

        # read input
        try:
            candidates = read_input(filename, input_encoding, reverse=options.reverse)
        except KeyboardInterrupt:
            exit_program("Canceled", show_help = False)

        # setup actions
        import percol.actions as actions
        if (options.quote):
            acts = (actions.output_to_stdout_double_quote, )
        else:
            acts = (actions.output_to_stdout, actions.output_to_stdout_double_quote)

        # arrange finder class
        candidate_finder_class = action_finder_class = decide_match_method(options)

        def set_finder_attribute_from_option(finder_instance):
            finder_instance.lazy_finding = not options.eager
            finder_instance.case_insensitive = not options.case_sensitive

        def set_if_not_none(src, dest, name):
            value = getattr(src, name)
            if value is not None:
                setattr(dest, name, value)

        with Percol(descriptors = tty.reconnect_descriptors(tty_f),
                    candidates = candidates,
                    actions = acts,
                    finder = candidate_finder_class,
                    action_finder = action_finder_class,
                    query = options.query,
                    caret = options.caret,
                    index = options.index,
                    encoding = output_encoding) as percol:
            # load run-command file
            load_rc(percol, options.rcfile, input_encoding)
            # evalutate strings specified by the option argument
            if options.string_to_eval is not None:
                eval_string(percol, options.string_to_eval, locale.getpreferredencoding())
            # finder settings from option values
            set_finder_attribute_from_option(percol.model_candidate.finder)
            set_finder_attribute_from_option(percol.model_action.finder)
            # view settings from option values
            set_if_not_none(options, percol.view, 'prompt_on_top')
            set_if_not_none(options, percol.view, 'results_top_down')
            # enter main loop
            if options.auto_fail and percol.one_or_zero_candidate == 0:
                exit_code = percol.cancel_with_exit_code()
            elif options.auto_match and percol.one_or_zero_candidate == 1:
                exit_code = percol.finish_with_exit_code()
            else:
                exit_code = percol.loop()

        exit(exit_code)
