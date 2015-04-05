# -*- coding: utf-8 -*-

import syslog
syslog.openlog("Percol")

def log(name, s = ""):
    syslog.syslog(syslog.LOG_ALERT, str(name) + ": " + str(s))

def dump(obj):
    import pprint
    pp = pprint.PrettyPrinter(indent=2)
    syslog.syslog(syslog.LOG_ALERT, str(name) + ": " + pp.pformat(obj))
    return obj
