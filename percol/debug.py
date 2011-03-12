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

import pprint

pp = pprint.PrettyPrinter(indent=2)

def log(name, s = ""):
    with open("/tmp/percol-log", "a") as f:
        f.write(str(name) + " : " + str(s) + "\n")

def dump(obj):
    with open("/tmp/percol-log", "a") as f:
        f.write(pp.pformat(obj) + "\n")
    return obj
