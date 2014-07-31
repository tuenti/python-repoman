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


class BaseIndexer(object):
    """
    Base class for all the indexers
    """
    _api = None
    _max_items = 500
    _repo_name = None

    def __init__(self, repo_name, url, user, password, api=None):
        self.url = url
        self.user = user
        self.password = password
        self._api = api
        self._repo_name = repo_name

    @property
    def repo_name(self):
        return self._repo_name


class IndexerError(Exception):
    pass
