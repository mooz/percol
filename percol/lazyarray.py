# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 mooz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

# ============================================================ #
# Lazy Array
# ============================================================ #

class LazyArray(object):
    """
    Wraps an iterable object and provides lazy array functionality,
    namely, lazy index access and iteration. Lazily got iteration
    results are cached and reused to provide consistent view
    for users.
    """

    def __init__(self, iterable_source):
        self.source = iterable_source
        self.got_elements = []
        self.read_count = 0

    def __len__(self):
        return len(self.got_elements)

    def __iter__(self):
        # yield cached result
        for elem in self.got_elements:
            yield elem
        # get results from iterable object
        for elem in self.source:
            self.read_count = self.read_count + 1
            self.got_elements.append(elem)
            yield elem

    def __getitem__(self, idx):
        # if element corresponds to specified index is not available,
        # get lacking results from iterable object
        from itertools import islice
        needed_read_count = max(idx - self.read_count + 1, 0)
        for elem in islice(self.source, 0, needed_read_count):
            self.read_count = self.read_count + 1
            self.got_elements.append(elem)
        return self.got_elements[idx]

if __name__ == "__main__":
    def getnumbers(n):
        for x in xrange(1, n):
            print("yield " + str(x))
            yield x
    larray = LazyArray(getnumbers(20))
    print("larray[7]: %d" % larray[7])
    for idx, x in enumerate(larray):
        print("larray[%d]: %d" % (idx, x))
    print("larray[10]: %d" % larray[10])
