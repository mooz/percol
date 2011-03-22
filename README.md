# percol

percol adds flavor of interactive selection to the traditional pipe concept on UNIX

## Installation

    $ git clone git://github.com/mooz/percol.git
    $ cd percol
    $ sudo python setup.py install

## Example

### zsh history search

In your `.zshrc`, put the lines below.

    function exists { which $1 &> /dev/null }
    
    if exists percol; then
        function percol_select_history() {
            local tac
            exists gtac && tac=gtac || tac=tac
            BUFFER="`$tac $HISTFILE | percol --query "$BUFFER"`"
            CURSOR=$#BUFFER         # move cursor
            zle -R -c               # refresh
        }
    
        zle -N percol_select_history
        bindkey '^R' percol_select_history
    fi

Then, you can display and search your zsh histories incrementally by pressing `Ctrl + r` key.
