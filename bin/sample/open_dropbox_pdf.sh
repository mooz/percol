#!/bin/sh

gnome-terminal --title "Find PDF files"  --hide-menubar \
    -e 'sh -c "evince \"$(find ~/Dropbox/ -name \"*.pdf\" -type f | percol)\""'
