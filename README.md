# percol

percol is an percolator.

## Example

### zsh history search

In your `.zshrc`, put the lines below.

    which percol > /dev/null
    if [ $0 ]; then
        function percol_select_history() {
            BUFFER="`tac ~/.histfile | percol`"
            zle -R -c               # refresh
        }
    
        zle -N percol_select_history
        bindkey '^R' percol_select_history
    fi

Then, you can display and search your zsh histories incrementally by pressing `Ctrl + r` key.
