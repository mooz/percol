# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 mooz
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

from abc import ABCMeta, abstractmethod

# ============================================================ #
# Finder
# ============================================================ #

class Finder(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        self.results_cache = {}

    smart_narrowing = False

    @abstractmethod
    def find(self, query, collection = None):
        pass

    def get_smart_collection(self, query):
        for i in xrange(len(query) - 1, 0, -1):
            q = query[0:i]
            if self.results_cache.has_key(q):
                return (line for (line, res, idx) in self.results_cache[q])
        return None

    def get_results(self, query):
        if self.results_cache.has_key(query):
            return self.results_cache[query]
        else:
            collection = None

            if self.smart_narrowing:
                collection = self.get_smart_collection(query)

            if collection is None:
                collection = self.collection

            results = [result for result in self.find(query, collection)]
            self.results_cache[query] = results
            return results

# ============================================================ #
# Finder > multiquery
# ============================================================ #

class FinderMultiQuery(Finder):
    def __init__(self, collection, split_str = " "):
        Finder.__init__(self)

        self.collection = collection
        self.split_str  = split_str

    case_insensitive = True

    dummy_res = [["", [(0, 0)]]]

    def find(self, query, collection = None):
        query_is_empty = query == ""

        # Arrange queries
        if self.case_insensitive:
            query = query.lower()
        queries = [self.transform_query(sub_query)
                   for sub_query in query.split(self.split_str)]

        if collection is None:
            collection = self.collection

        for idx, line in enumerate(collection):
            if query_is_empty:
                res = self.dummy_res
            else:
                if self.case_insensitive:
                    line_to_match = line.lower()
                else:
                    line_to_match = line
                res = self.find_queries(queries, line_to_match)

            if res:
                yield line, res, idx

    and_search = True

    def find_queries(self, sub_queries, line):
        res = []

        and_search = self.and_search

        for subq in sub_queries:
            if subq:
                find_info = self.find_query(subq, line)
                if find_info:
                    res.append((subq, find_info))
                elif and_search:
                    return None
        return res

    @abstractmethod
    def find_query(self, needle, haystack):
        # return [(pos1, pos1_len), (pos2, pos2_len), ...]
        #
        # where `pos1', `pos2', ... are begining positions of all occurence of needle in `haystack'
        # and `pos1_len', `pos2_len', ... are its length.
        pass

    # override this method if needed
    def transform_query(self, query):
        return query

# ============================================================ #
# Finder > AND search
# ============================================================ #

class FinderMultiQueryString(FinderMultiQuery):
    smart_narrowing = True

    def find_query(self, needle, haystack):
        stride = len(needle)
        start  = 0
        res    = []

        while True:
            found = haystack.find(needle, start)
            if found < 0:
                break
            res.append((found, stride))
            start = found + stride

        return res

# ============================================================ #
# Finder > AND search > Regular Expression
# ============================================================ #

class FinderMultiQueryRegex(FinderMultiQuery):
    import re

    def transform_query(self, needle):
        try:
            return re.compile(needle)
        except:
            return None

    def find_query(self, needle, haystack):
        try:
            matched = needle.search(haystack)
            return [(matched.start(), matched.end() - matched.start())]
        except:
            return None
