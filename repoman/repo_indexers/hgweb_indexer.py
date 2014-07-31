#!/usr/bin/env python
#
# Copyright 2014 Tuenti Technologies S.L.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from repoman.repo_indexers.base_indexer import BaseIndexer
from repoman.hg.hgwebapi import HGWebApi


class HGWebIndexer(BaseIndexer):
    """
    Indexer for HGWeb
    """
    @property
    def api(self):
        if not self._api:
            self._api = HGWebApi(self.url, self.user, self.password)
        return self._api

    def get_branches(self, limit=None):
        limit = limit if limit else self._max_items
        return self.api.get_branches(self.repo_name, limit)

    def get_branch_log(self, branch_name, limit=None):
        """
        Not implemented, need to adapt the raw output for the changesets log
        """
        return None
