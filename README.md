# percol

percol adds flavor of interactive selection to the traditional pipe concept on UNIX

## Installation

First, clone percol repository and go into the directory.

    $ git clone git://github.com/mooz/percol.git
    $ cd percol

Then, run a command below.

    $ sudo python setup.py install

If you don't have a root permission (or don't wanna install percol with sudo), try next one.

    $ python setup.py install --prefix=~/.local
    $ export PATH=~/.local/bin:$PATH

## Example

### Basic (and crappy) examples

Specifying a filename.

    $ percol /var/log/syslog

Specifying a redirecition.

    $ ps aux | percol

### zsh history search

In your `.zshrc`, put the lines below.

    function exists { which $1 &> /dev/null }
    
    if exists percol; then
        function percol_select_history() {
            local tac
            exists gtac && tac=gtac || tac=tac
            BUFFER=$($tac $HISTFILE | sed 's/^: [0-9]*:[0-9]*;//' | percol --query "$LBUFFER")
            CURSOR=$#BUFFER         # move cursor
            zle -R -c               # refresh
        }
    
        zle -N percol_select_history
        bindkey '^R' percol_select_history
    fi

Then, you can display and search your zsh histories incrementally by pressing `Ctrl + r` key.

### tmux

Here are some examples of tmux and percol integration.

    bind b split-window "tmux lsw | percol --initial-index $(tmux lsw | awk '/active.$/ {print NR-1}') | cut -d':' -f 1 | xargs tmux select-window -t"
    bind B split-window "tmux ls | percol --initial-index $(tmux ls | awk '/attached.$/ {print NR-1}') | cut -d':' -f 1 | xargs tmux switch-client -t"

By putting above 2 settings into `tmux.conf`, you can select a tmux window with `${TMUX_PREFIX} b` keys and session with `${TMUX_PREFIX} B` keys.

## Configuration

Configuration file for percol should be placed under `${HOME}/.percol.d/` and named `rc.py`.

Here is an example `~/.percol.d/rc.py`. 

    # X / _ / X
    percol.view.PROMPT  = ur"<bold><yellow>X / _ / X</yellow></bold> %q"
    
    # Emacs like
    percol.import_keymap({
        "C-h" : lambda percol: percol.command.delete_backward_char(),
        "C-d" : lambda percol: percol.command.delete_forward_char(),
        "C-k" : lambda percol: percol.command.kill_end_of_line(),
        "C-y" : lambda percol: percol.command.yank(),
        "C-a" : lambda percol: percol.command.beginning_of_line(),
        "C-e" : lambda percol: percol.command.end_of_line(),
        "C-b" : lambda percol: percol.command.backward_char(),
        "C-f" : lambda percol: percol.command.forward_char(),
        "C-n" : lambda percol: percol.command.select_next(),
        "C-p" : lambda percol: percol.command.select_previous(),
        "C-v" : lambda percol: percol.command.select_next_page(),
        "M-v" : lambda percol: percol.command.select_previous_page(),
        "M-<" : lambda percol: percol.command.select_top(),
        "M->" : lambda percol: percol.command.select_bottom(),
        "C-m" : lambda percol: percol.finish(),
        "C-j" : lambda percol: percol.finish(),
        "C-g" : lambda percol: percol.cancel(),
    })
