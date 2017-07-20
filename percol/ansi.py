# -*- coding: utf-8 -*-

from percol.markup import MarkupParser

import sys
import re

# http://graphcomp.com/info/specs/ansi_col.html

DISPLAY_ATTRIBUTES = {
    "reset"      : 0,
    "bold"       : 1,
    "bright"     : 1,
    "dim"        : 2,
    "underline"  : 4,
    "underscore" : 4,
    "blink"      : 5,
    "reverse"    : 7,
    "hidden"     : 8,
    # Colors
    "black"      : 30,
    "red"        : 31,
    "green"      : 32,
    "yellow"     : 33,
    "blue"       : 34,
    "magenta"    : 35,
    "cyan"       : 36,
    "white"      : 37,
    "on_black"   : 40,
    "on_red"     : 41,
    "on_green"   : 42,
    "on_yellow"  : 43,
    "on_blue"    : 44,
    "on_magenta" : 45,
    "on_cyan"    : 46,
    "on_white"   : 47,
}

markup_parser = MarkupParser()

def markup(string):
    return decorate_parse_result(markup_parser.parse(string))

def remove_escapes(string):
    return re.sub(r"\x1B\[(?:[0-9]{1,2}(?:;[0-9]{1,2})?)?[m|K]", "", string)

def decorate_parse_result(parse_result):
    decorated_string = ""
    for (fragment_string, attributes) in parse_result:
        decorated_string += decorate_string_with_attributes(fragment_string, attributes)
    return decorated_string

def decorate_string_with_attributes(string, attributes):
    attribute_numbers = attribute_names_to_numbers(attributes)
    attribute_format = ";".join(attribute_numbers)
    return "\033[{0}m{1}\033[0m".format(attribute_format, string)

def attribute_names_to_numbers(attribute_names):
    return [str(DISPLAY_ATTRIBUTES[name])
            for name in attribute_names
            if name in DISPLAY_ATTRIBUTES]

if __name__ == "__main__":
    tests = (
        "hello",
        "hello <red>red</red> normal",
        "hello <on_green>with background green <underline>this is underline <red>and red</red></underline></on_green> then, normal",
        "baaaaa<green>a<blue>aa</green>a</blue>aaaaaaa", # unmatch
        "baaaaa<green>a<blue>aa</blue>a</green>aaaaaaa",
        "<underline>hello \\<red>red\\</red> normal</underline>",  # escape
        u"マルチ<magenta>バイト<blue>文字</blue>の</magenta>テスト", # multibyte
    )

    for test in tests:
        try:
            print("----------------------------------------------------------")
            print(markup(test))
        except Exception as e:
            print("fail: " + str(e))
