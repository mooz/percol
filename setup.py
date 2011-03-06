#/usr/bin/env python

from distutils.core import setup

import percol

setup(name             = "percol",
      version          = percol.__version__,
      author           = "mooz",
      author_email     = "stillpedant@gmail.com",
      url              = "https://github.com/mooz/percol",
      description      = "Adds flavor of interactive filtering to the traditional pipe concept of shell",
      long_description = percol.__doc__,
      packages         = ["percol"],
      scripts          = ["bin/percol"],
      classifiers      = ["Environment :: Console :: Curses",
                          "License :: OSI Approved :: MIT License",
                          "Operating System :: POSIX",
                          "Programming Language :: Python",
                          "Topic :: Text Processing :: Filters",
                          "Topic :: Text Editors :: Emacs",
                          "Topic :: Utilities"],
      keywords         = "anything.el unite.vim dmenu shell pipe filter curses",
      license          = "MIT",
      )
