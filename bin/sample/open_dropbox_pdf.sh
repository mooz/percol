#!/bin/sh

gnome-terminal --title "Find PDF files"  --hide-menubar \
    -x sh -c "find ~/Dropbox/ -name \"*.pdf\" -type f | percol --quote | xargs evince"
