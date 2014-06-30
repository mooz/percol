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

import sys, six

from percol.action import action

def double_quote_string(string):
    return '"' + string.replace('"', r'\"') + '"'

def get_raw_stream(stream):
    if six.PY2:
        return stream
    else:
        return stream.buffer

@action()
def output_to_stdout(lines, percol):
    "output marked (selected) items to stdout"
    stdout = get_raw_stream(sys.stdout)
    for line in lines:
        stdout.write(percol.display.get_raw_string(line))
        stdout.write(six.b("\n"))

@action()
def output_to_stdout_double_quote(lines, percol):
    "output marked (selected) items to stdout with double quotes"
    stdout = get_raw_stream(sys.stdout)
    for line in lines:
        stdout.write(percol.display.get_raw_string(double_quote_string(line)))
        stdout.write(six.b("\n"))
