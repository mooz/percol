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

import curses, array
import six

SPECIAL_KEYS = {
    curses.KEY_A1        : "<a1>",
    curses.KEY_A3        : "<a3>",
    curses.KEY_B2        : "<b2>",
    curses.KEY_BACKSPACE : "<backspace>",
    curses.KEY_BEG       : "<beg>",
    curses.KEY_BREAK     : "<break>",
    curses.KEY_BTAB      : "<btab>",
    curses.KEY_C1        : "<c1>",
    curses.KEY_C3        : "<c3>",
    curses.KEY_CANCEL    : "<cancel>",
    curses.KEY_CATAB     : "<catab>",
    curses.KEY_CLEAR     : "<clear>",
    curses.KEY_CLOSE     : "<close>",
    curses.KEY_COMMAND   : "<command>",
    curses.KEY_COPY      : "<copy>",
    curses.KEY_CREATE    : "<create>",
    curses.KEY_CTAB      : "<ctab>",
    curses.KEY_DC        : "<dc>",
    curses.KEY_DL        : "<dl>",
    curses.KEY_DOWN      : "<down>",
    curses.KEY_EIC       : "<eic>",
    curses.KEY_END       : "<end>",
    curses.KEY_ENTER     : "<enter>",
    curses.KEY_EOL       : "<eol>",
    curses.KEY_EOS       : "<eos>",
    curses.KEY_EXIT      : "<exit>",
    curses.KEY_F0        : "<f0>",
    curses.KEY_F1        : "<f1>",
    curses.KEY_F10       : "<f10>",
    curses.KEY_F11       : "<f11>",
    curses.KEY_F12       : "<f12>",
    curses.KEY_F13       : "<f13>",
    curses.KEY_F14       : "<f14>",
    curses.KEY_F15       : "<f15>",
    curses.KEY_F16       : "<f16>",
    curses.KEY_F17       : "<f17>",
    curses.KEY_F18       : "<f18>",
    curses.KEY_F19       : "<f19>",
    curses.KEY_F2        : "<f2>",
    curses.KEY_F20       : "<f20>",
    curses.KEY_F21       : "<f21>",
    curses.KEY_F22       : "<f22>",
    curses.KEY_F23       : "<f23>",
    curses.KEY_F24       : "<f24>",
    curses.KEY_F25       : "<f25>",
    curses.KEY_F26       : "<f26>",
    curses.KEY_F27       : "<f27>",
    curses.KEY_F28       : "<f28>",
    curses.KEY_F29       : "<f29>",
    curses.KEY_F3        : "<f3>",
    curses.KEY_F30       : "<f30>",
    curses.KEY_F31       : "<f31>",
    curses.KEY_F32       : "<f32>",
    curses.KEY_F33       : "<f33>",
    curses.KEY_F34       : "<f34>",
    curses.KEY_F35       : "<f35>",
    curses.KEY_F36       : "<f36>",
    curses.KEY_F37       : "<f37>",
    curses.KEY_F38       : "<f38>",
    curses.KEY_F39       : "<f39>",
    curses.KEY_F4        : "<f4>",
    curses.KEY_F40       : "<f40>",
    curses.KEY_F41       : "<f41>",
    curses.KEY_F42       : "<f42>",
    curses.KEY_F43       : "<f43>",
    curses.KEY_F44       : "<f44>",
    curses.KEY_F45       : "<f45>",
    curses.KEY_F46       : "<f46>",
    curses.KEY_F47       : "<f47>",
    curses.KEY_F48       : "<f48>",
    curses.KEY_F49       : "<f49>",
    curses.KEY_F5        : "<f5>",
    curses.KEY_F50       : "<f50>",
    curses.KEY_F51       : "<f51>",
    curses.KEY_F52       : "<f52>",
    curses.KEY_F53       : "<f53>",
    curses.KEY_F54       : "<f54>",
    curses.KEY_F55       : "<f55>",
    curses.KEY_F56       : "<f56>",
    curses.KEY_F57       : "<f57>",
    curses.KEY_F58       : "<f58>",
    curses.KEY_F59       : "<f59>",
    curses.KEY_F6        : "<f6>",
    curses.KEY_F60       : "<f60>",
    curses.KEY_F61       : "<f61>",
    curses.KEY_F62       : "<f62>",
    curses.KEY_F63       : "<f63>",
    curses.KEY_F7        : "<f7>",
    curses.KEY_F8        : "<f8>",
    curses.KEY_F9        : "<f9>",
    curses.KEY_FIND      : "<find>",
    curses.KEY_HELP      : "<help>",
    curses.KEY_HOME      : "<home>",
    curses.KEY_IC        : "<ic>",
    curses.KEY_IL        : "<il>",
    curses.KEY_LEFT      : "<left>",
    curses.KEY_LL        : "<ll>",
    curses.KEY_MARK      : "<mark>",
    curses.KEY_MAX       : "<max>",
    curses.KEY_MESSAGE   : "<message>",
    curses.KEY_MIN       : "<min>",
    curses.KEY_MOUSE     : "<mouse>",
    curses.KEY_MOVE      : "<move>",
    curses.KEY_NEXT      : "<next>",
    curses.KEY_NPAGE     : "<npage>",
    curses.KEY_OPEN      : "<open>",
    curses.KEY_OPTIONS   : "<options>",
    curses.KEY_PPAGE     : "<ppage>",
    curses.KEY_PREVIOUS  : "<previous>",
    curses.KEY_PRINT     : "<print>",
    curses.KEY_REDO      : "<redo>",
    curses.KEY_REFERENCE : "<reference>",
    curses.KEY_REFRESH   : "<refresh>",
    curses.KEY_REPLACE   : "<replace>",
    curses.KEY_RESET     : "<reset>",
    curses.KEY_RESIZE    : "<resize>",
    curses.KEY_RESTART   : "<restart>",
    curses.KEY_RESUME    : "<resume>",
    curses.KEY_RIGHT     : "<right>",
    curses.KEY_SAVE      : "<save>",
    curses.KEY_SBEG      : "<sbeg>",
    curses.KEY_SCANCEL   : "<scancel>",
    curses.KEY_SCOMMAND  : "<scommand>",
    curses.KEY_SCOPY     : "<scopy>",
    curses.KEY_SCREATE   : "<screate>",
    curses.KEY_SDC       : "<sdc>",
    curses.KEY_SDL       : "<sdl>",
    curses.KEY_SELECT    : "<select>",
    curses.KEY_SEND      : "<send>",
    curses.KEY_SEOL      : "<seol>",
    curses.KEY_SEXIT     : "<sexit>",
    curses.KEY_SF        : "<sf>",
    curses.KEY_SFIND     : "<sfind>",
    curses.KEY_SHELP     : "<shelp>",
    curses.KEY_SHOME     : "<shome>",
    curses.KEY_SIC       : "<sic>",
    curses.KEY_SLEFT     : "<sleft>",
    curses.KEY_SMESSAGE  : "<smessage>",
    curses.KEY_SMOVE     : "<smove>",
    curses.KEY_SNEXT     : "<snext>",
    curses.KEY_SOPTIONS  : "<soptions>",
    curses.KEY_SPREVIOUS : "<sprevious>",
    curses.KEY_SPRINT    : "<sprint>",
    curses.KEY_SR        : "<sr>",
    curses.KEY_SREDO     : "<sredo>",
    curses.KEY_SREPLACE  : "<sreplace>",
    curses.KEY_SRESET    : "<sreset>",
    curses.KEY_SRIGHT    : "<sright>",
    curses.KEY_SRSUME    : "<srsume>",
    curses.KEY_SSAVE     : "<ssave>",
    curses.KEY_SSUSPEND  : "<ssuspend>",
    curses.KEY_STAB      : "<stab>",
    curses.KEY_SUNDO     : "<sundo>",
    curses.KEY_SUSPEND   : "<suspend>",
    curses.KEY_UNDO      : "<undo>",
    curses.KEY_UP        : "<up>",
}

# TODO: Better to use ord(curses.erasechar()) instead of 127
SPECIAL_KEYS[8] = SPECIAL_KEYS[127] = "<backspace>"

# Other
KEY_ESCAPE = 27

class KeyHandler(object):
    def __init__(self, screen):
        self.screen = screen

    def get_key_for(self, ch, escaped = False):
        k = None

        if self.is_displayable_key(ch):
            k = self.displayable_key_to_str(ch)
        elif ch in SPECIAL_KEYS:
            k = SPECIAL_KEYS[ch]
        elif self.is_ctrl_masked_key(ch):
            k = self.ctrl_masked_key_to_str(ch)
        elif ch == KEY_ESCAPE:
            if escaped:
                k = "ESC"
            else:
                k = "M-" + self.get_key_for(self.screen.getch(), escaped = True)
        elif ch == -1:
            k = "C-c"
        return k

    def get_utf8_key_for(self, ch):
        buf = array.array("B", [ch])
        buf.extend(self.screen.getch() for i in six.moves.range(1, self.get_utf8_count(ch)))
        return buf.tostring().decode("utf-8")

    def is_utf8_multibyte_key(self, ch):
        return (ch & 0b11000000) == 0b11000000

    utf8_skip_data = [
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 1, 1
    ]

    def get_utf8_count(self, ch):
        return self.utf8_skip_data[ch]

    def displayable_key_to_str(self, ch):
        return chr(ch)

    def is_displayable_key(self, ch):
        return 32 <= ch <= 126

    def is_ctrl_masked_key(self, ch):
        return 0 <= ch <= 31 and ch != KEY_ESCAPE

    def ctrl_masked_key_to_str(self, ch):
        s = "C-"

        if ch == 0:
            s += "SPC"
        elif 0 < ch <= 27:
            s += chr(ch + 96)  # ord('a') => 97, CTRL_A => 1
        else:
            s += "UNKNOWN ({0:d} :: 0x{0:x})".format(ch)

        return s
