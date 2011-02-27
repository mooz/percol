#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

from percol import Percol

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
            except OSError:
                # maybe mode specification is invalid or /dev/null is specified (?)
                target[name] = None
                print("Failed to open {0}".format(other_desc))

    return target

def print_usage():
    print("""\
Usage: {0} [TTY]
  TTY  path to the tty (usually, $TTY)\
""".format(__file__))

if __name__ == "__main__":
    ttyname = sys.argv[1] if len(sys.argv) > 1 else get_ttyname()

    if not ttyname:
        print_usage()
        exit(1)

    with open(ttyname, "r+w") as tty:
        target = reconnect_descriptors(tty)

        with Percol(target) as percol:
            percol.loop()
