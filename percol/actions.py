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

import sys

from percol.action import action

def double_quote_string(string):
    return '"' + string.replace('"', r'\"') + '"'

@action()
def output_to_stdout(lines, percol):
    "output marked (selected) items to stdout"
    for line in lines:
        sys.stdout.write(percol.display.get_raw_string(line))
        sys.stdout.write("\n")

@action()
def output_to_stdout_double_quote(lines, percol):
    "output marked (selected) items to stdout with double quotes"
    for line in lines:
        sys.stdout.write(percol.display.get_raw_string(double_quote_string(line)))
        sys.stdout.write("\n")
