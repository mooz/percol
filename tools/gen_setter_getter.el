(loop for name in '("query"
                    "old_query"
                    "index"
                    "caret"
                    "marks"
                    "results"
                    "results_generator"
                    "results_cache"
                    "finder")
      do
      (insert (replace-regexp-in-string (rx "%NAME%") name
                                        "
    @property
    def %NAME%(self):
        return self.status[\"%NAME%\"]
    @%NAME%.setter
    def %NAME%(self, value):
        self.status[\"%NAME%\"] = value
" t)))
