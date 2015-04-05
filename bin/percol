#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys

# add load path
if __name__ == '__main__':
    libdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    if os.path.exists(os.path.join(libdir, "percol")):
        sys.path.insert(0, libdir)

from percol.cli import main

main()
