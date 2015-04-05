# -*- coding: utf-8 -*-

import six

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
        # if the element corresponds to the specified index is not
        # available, pull results from iterable object
        if idx < 0:
            self.pull_all()
        else:
            from itertools import islice
            for elem in islice(self, 0, idx + 1):
                pass

        return self.got_elements[idx]

    def pull_all(self):
        for elem in self:
            pass

    def has_nth_value(self, nth):
        try:
            self[nth]
            return True
        except IndexError:
            return False

if __name__ == "__main__":
    def getnumbers(n):
        for x in six.moves.range(1, n):
            print("yield " + str(x))
            yield x
    larray = LazyArray(getnumbers(20))
    print("larray[7]: %d" % larray[7])
    for idx, x in enumerate(larray):
        print("larray[%d]: %d" % (idx, x))
    print("larray[10]: %d" % larray[10])

    larray2 = LazyArray(getnumbers(20))
    print("larray2[-1]: %d" % larray2[-1])
