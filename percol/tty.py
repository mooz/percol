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
import os

def get_ttyname():
    for f in sys.stdin, sys.stdout, sys.stderr:
        if f.isatty():
            return os.ttyname(f.fileno())
    return None

def reconnect_descriptors(tty):
    target = {}

    stdios = (("stdin", "r"), ("stdout", "w"), ("stderr", "w"))

    tty_desc = tty.fileno()

    for name, mode in stdios:
        f = getattr(sys, name)

        if f.isatty():
            # f is TTY
            target[name] = f
        else:
            # f is other process's output / input or a file

            # save descriptor connected with other process
            std_desc = f.fileno()
            other_desc = os.dup(std_desc)

            # set std descriptor. std_desc become invalid.
            os.dup2(tty_desc, std_desc)

            # set file object connected to other_desc to corresponding one of sys.{stdin, stdout, stderr}
            try:
                target[name] = os.fdopen(other_desc, mode)
                setattr(sys, name, target[name])
            except OSError:
                # maybe mode specification is invalid or /dev/null is specified (?)
                target[name] = None
                print("Failed to open {0}".format(other_desc))

    return target
