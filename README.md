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
            BUFFER=`$tac $HISTFILE | percol --query "$BUFFER"`
            CURSOR=$#BUFFER         # move cursor
            zle -R -c               # refresh
        }
    
        zle -N percol_select_history
        bindkey '^R' percol_select_history
    fi

Then, you can display and search your zsh histories incrementally by pressing `Ctrl + r` key.

## Configuration

Configuration file for percol should be placed under `${HOME}/.percol.d/` and named `rc.py`.

Here is the example `~/.percol.d/rc.py`. 

    # X / _ / X
    percol.view.PROMPT  = ur"<bold><yellow>X / _ / X</yellow></bold> %q"
    
    # Emacs like
    percol.import_keymap({
        "C-h" : lambda percol: percol.model.delete_backward_char(),
        "C-d" : lambda percol: percol.model.delete_forward_char(),
        "C-k" : lambda percol: percol.model.kill_end_of_line(),
        "C-y" : lambda percol: percol.model.yank(),
        "C-a" : lambda percol: percol.model.beginning_of_line(),
        "C-e" : lambda percol: percol.model.end_of_line(),
        "C-b" : lambda percol: percol.model.backward_char(),
        "C-f" : lambda percol: percol.model.forward_char(),
        "C-n" : lambda percol: percol.model.select_next(),
        "C-p" : lambda percol: percol.model.select_previous(),
        "C-v" : lambda percol: percol.select_next_page(),
        "M-v" : lambda percol: percol.select_previous_page(),
        "M-<" : lambda percol: percol.model.select_top(),
        "M->" : lambda percol: percol.model.select_bottom(),
        "C-m" : lambda percol: percol.finish(),
        "C-j" : lambda percol: percol.finish(),
        "C-g" : lambda percol: percol.cancel(),
    })
