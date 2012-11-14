# percol

                                    __
        ____  ___  ______________  / /
       / __ \/ _ \/ ___/ ___/ __ \/ /
      / /_/ /  __/ /  / /__/ /_/ / /
     / .___/\___/_/   \___/\____/_/
    /_/

percol adds flavor of interactive selection to the traditional pipe concept on UNIX

- [Installation](#installation)
- [Usage](#usage)
- [Example](#example)
    - [Interactive pgrep / pkill](#interactive-pgrep--pkill)
    - [zsh history search](#zsh-history-search)
    - [tmux](#tmux)
- [Configuration](#configuration)
    - [Customizing styles](#customizing-styles)
        - [Foreground Colors](#foreground-colors)
        - [Background Color](#background-color)
        - [Attributes](#attributes)
- [Matching Method](#matching-method)
    - [Migemo support](#migemo-support)
        - [Dictionary settings](#dictionary-settings)
        - [Minimum query length](#minimum-query-length)
    - [Switching matching method dynamically](#switching-matching-method-dynamically)
- [Tips](#tips)
    - [Selecting multiple candidates](#selecting-multiple-candidates)
    - [Z Shell support](#z-shell-support)

## Installation

First, clone percol repository and go into the directory.

    $ git clone git://github.com/mooz/percol.git
    $ cd percol

Then, run a command below.

    $ sudo python setup.py install

If you don't have a root permission (or don't wanna install percol with sudo), try next one.

    $ python setup.py install --prefix=~/.local
    $ export PATH=~/.local/bin:$PATH

## Usage

Specifying a filename.

    $ percol /var/log/syslog

Specifying a redirecition.

    $ ps aux | percol

## Example

### Interactive pgrep / pkill

Here is an interactive version of pgrep,

    $ ps aux | percol | awk '{ print $2 }'

and here is an interactive version of pkill.

    $ ps aux | percol | awk '{ print $2 }' | xargs kill

For zsh users, command versions are here (`ppkill` accepts options like `-9`).

```sh
function ppgrep() {
    if [[ $1 == "" ]]; then
        PERCOL=percol
    else
        PERCOL="percol --query $1"
    fi
    ps aux | eval $PERCOL | awk '{ print $2 }'
}

function ppkill() {
    if [[ $1 =~ "^-" ]]; then
        QUERY=""            # options only
    else
        QUERY=$1            # with a query
        [[ $# > 0 ]] && shift
    fi
    ppgrep $QUERY | xargs kill $*
}
```

### zsh history search

In your `.zshrc`, put the lines below.

```sh
function exists { which $1 &> /dev/null }

if exists percol; then
    function percol_select_history() {
        local tac
        exists gtac && tac="gtac" || exists tac && tac="tac" || tac="tail -r"
        BUFFER=$(history -n 1 | eval $tac | percol --query "$LBUFFER")
        CURSOR=$#BUFFER         # move cursor
        zle -R -c               # refresh
    }

    zle -N percol_select_history
    bindkey '^R' percol_select_history
fi
```

Then, you can display and search your zsh histories incrementally by pressing `Ctrl + r` key.

### tmux

Here are some examples of tmux and percol integration.

    bind b split-window "tmux lsw | percol --initial-index $(tmux lsw | awk '/active.$/ {print NR-1}') | cut -d':' -f 1 | xargs tmux select-window -t"
    bind B split-window "tmux ls | percol --initial-index $(tmux ls | awk '/attached.$/ {print NR-1}') | cut -d':' -f 1 | xargs tmux switch-client -t"

By putting above 2 settings into `tmux.conf`, you can select a tmux window with `${TMUX_PREFIX} b` keys and session with `${TMUX_PREFIX} B` keys.

## Configuration

Configuration file for percol should be placed under `${HOME}/.percol.d/` and named `rc.py`.

Here is an example `~/.percol.d/rc.py`.

```python
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
```

### Customizing styles

For now, styles of following 4 items can be customized in `rc.py`.

```python
percol.view.CANDIDATES_LINE_BASIC    = ("on_default", "default")
percol.view.CANDIDATES_LINE_SELECTED = ("underline", "on_yellow", "white")
percol.view.CANDIDATES_LINE_MARKED   = ("bold", "on_cyan", "black")
percol.view.CANDIDATES_LINE_QUERY    = ("yellow", "bold")
```

Each RHS is a tuple of style specifiers listed below.

#### Foreground Colors

- `"black"`   for `curses.COLOR_BLACK`
- `"red"`     for `curses.COLOR_RED`
- `"green"`   for `curses.COLOR_GREEN`
- `"yellow"`  for `curses.COLOR_YELLOW`
- `"blue"`    for `curses.COLOR_BLUE`
- `"magenta"` for `curses.COLOR_MAGENTA`
- `"cyan"`    for `curses.COLOR_CYAN`
- `"white"`   for `curses.COLOR_WHITE`

#### Background Color

- `"on_black"`   for `curses.COLOR_BLACK`
- `"on_red"`     for `curses.COLOR_RED`
- `"on_green"`   for `curses.COLOR_GREEN`
- `"on_yellow"`  for `curses.COLOR_YELLOW`
- `"on_blue"`    for `curses.COLOR_BLUE`
- `"on_magenta"` for `curses.COLOR_MAGENTA`
- `"on_cyan"`    for `curses.COLOR_CYAN`
- `"on_white"`   for `curses.COLOR_WHITE`

#### Attributes

- `"altcharset"` for `curses.A_ALTCHARSET`
- `"blink"`      for `curses.A_BLINK`
- `"bold"`       for `curses.A_BOLD`
- `"dim"`        for `curses.A_DIM`
- `"normal"`     for `curses.A_NORMAL`
- `"standout"`   for `curses.A_STANDOUT`
- `"underline"`  for `curses.A_UNDERLINE`

## Matching Method

By default, percol interprets input queries by users as **string**. If you prefer **regular expression**, try `--match-method` command line option.

    $ percol --match-method regex

### Migemo support

From version 0.0.2, percol supports **migemo** (http://0xcc.net/migemo/) for `--match-method` experimentally.

    $ percol --match-method migemo

This feature requires following external modules for now.

- C/Migemo (http://code.google.com/p/cmigemo/)
- PyMigemo (http://www.atzm.org/etc/pymigemo.html)

#### Dictionary settings

By default, percol assumes the path of a dictionary for migemo is `/usr/local/share/migemo/utf-8/migemo-dict`. If the dictionary is located in a different place, you should tell the location via `rc.py`.

For example, if the path of the dictionary is `/path/to/a/migemo-dict`, put lines below into your `rc.py`.

```python
from percol.finder import FinderMultiQueryMigemo
FinderMultiQueryMigemo.dictionary_path = "/path/to/a/migemo-dict"
```

#### Minimum query length

If the query length is **too short**, migemo generates **very long** regular expression. To deal with this problem, percol does not pass a query if the length of the query is shorter than **2** and treat the query as raw regular expression.

To change this behavior, change the value of `FinderMultiQueryMigemo.minimum_query_length` like following settings.

```python
from percol.finder import FinderMultiQueryMigemo
FinderMultiQueryMigemo.minimum_query_length = 1
```

### Switching matching method dynamically

Matching method can be switched dynamically (at run time) by executing `percol.command.specify_finder(FinderClass)` or `percol.command.toggle_finder(FinderClass)`. In addition, `percol.command.specify_case_sensitive(case_sensitive)` and `percol.command.toggle_case_sensitive()` change the matching status of case sensitivity.

```python
from percol.finder import FinderMultiQueryMigemo, FinderMultiQueryRegex
percol.import_keymap({
    "M-c" : lambda percol: percol.command.toggle_case_sensitive(),
    "M-m" : lambda percol: percol.command.toggle_finder(FinderMultiQueryMigemo),
    "M-r" : lambda percol: percol.command.toggle_finder(FinderMultiQueryRegex)
})
```

## Tips

### Selecting multiple candidates

You can select and let percol to output multiple candidates by `percol.command.toggle_mark_and_next()` (which is bound to `C-SPC` by default).

`percol.command.mark_all()`, `percol.command.unmark_all()` and `percol.command.toggle_mark_all()` are useful to mark / unmark all candidates at once.

## Z Shell support

A zsh completing-function for percol is available in https://github.com/mooz/percol/blob/master/tools/zsh/_percol .
