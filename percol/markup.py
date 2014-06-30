# -*- coding: utf-8 -*-
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

class MarkupParser(object):
    def __init__(self):
        pass

    def parse(self, s):
        self.init_status(s)
        self.parse_string()
        self.consume_token()

        return self.tokens

    def init_status(self, s):
        self.s = s
        self.pos = 0
        self.tokens = []
        self.tags = []
        self.buffer = []

    def consume_token(self):
        if self.buffer:
            self.tokens.append(("".join(self.buffer), list(self.tags)))
            self.buffer[:] = []

    def get_next_char(self):
        try:
            p = self.pos
            self.pos += 1
            return self.s[p]
        except IndexError:
            return None

    def get_next_chars(self):
        s_len = len(self.s)
        while self.pos < s_len:
            yield self.get_next_char()

    def peek_next_char(self):
        try:
            return self.s[self.pos]
        except IndexError:
            return None

    def parse_string(self):
        escaped = False

        for c in self.get_next_chars():
            if escaped:
                escaped = False
                self.buffer.append(c)
            elif c == '\\':
                    escaped = True
            elif c == '<':
                self.consume_token()

                if self.peek_next_char() == '/':
                    # end certain tag
                    self.get_next_char()
                    tag = self.parse_tag()

                    try:
                        self.tags.remove(tag)
                    except:
                        raise Exception("corresponding beginning tag for </{0}> is not found".format(tag))
                else:
                    # begin new tag
                    tag = self.parse_tag()
                    self.tags.insert(0, tag) # front
            else:
                self.buffer.append(c)

    def parse_tag(self):
        buf = []
        escaped = False

        for c in self.get_next_chars():
            if escaped:
                buf.append(c)
            elif c == '\\':
                escaped = True
            elif c == '>':
                return "".join(buf)
            else:
                buf.append(c)

        raise Exception("Unclosed tag " + "".join(buf))

if __name__ == "__main__":
    import pprint, sys, six

    parser = MarkupParser()

    def color(str, color = 31):
        colors = {
            "black"      : 30,
            "red"        : 31,
            "green"      : 32,
            "yellow"     : 33,
            "blue"       : 34,
            "magenta"    : 35,
            "cyan"       : 36,
            "white"      : 37,
            "on_black"   : 40,
            "on_red"     : 41,
            "on_green"   : 42,
            "on_yellow"  : 43,
            "on_blue"    : 44,
            "on_magenta" : 45,
            "on_cyan"    : 46,
            "on_white"   : 47,
        }

        if isinstance(color, six.string_types):
            try:
                color = colors[color]
            except:
                color = colors["white"]

        if sys.stdout.isatty():
            return "\033[1;{0}m{1}\033[0m".format(color, str)
        else:
            return str

    tests = (
        "hello",
        "hello <red>red</red> normal",
        "hello <on_green>with background green <bold>this is bold <red>and red</red></bold></on_green> then, normal",
        "baaaaa<green>a<blue>aa</green>a</blue>aaaaaaa", # unmatch
        "baaaaa<green>a<blue>aa</blue>a</green>aaaaaaa",
        "hello \\<red>red\\</red> normal",  # escape
        u"マルチ<magenta>バイト<blue>文字</blue>の</magenta>テスト", # multibyte
    )

    for test in tests:
        try:
            print("----------------------------------------------------------")
            print("Testing [%s]" % color(test, "cyan"))
            print(color("pass: " + pprint.pformat(parser.parse(test)), "green"))
        except Exception as e:
            print(color("fail: " + str(e), "red"))
