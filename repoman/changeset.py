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


class Changeset(tuple):

    SHORT_HASH_COUNT = 12

    # Caching branches as get them could be an expensive task
    _branches = None

    def __new__(cls, repo, inital_values):
        values = (repo,) + (inital_values)
        return tuple.__new__(cls, values)

    def __str__(self):
        """
        Cutting down the hash string to 12 characters to show short form
        to avoid very large messages formed by hashes
        """
        return "%s" % self.hash[:self.SHORT_HASH_COUNT]

    @property
    def repository(self):
        return self[0]

    @property
    def merge(self):
        if self.repository:
            return self.repository.is_merge(self.hash)
        else:
            return None

    @property
    def parents(self):
        if self.repository:
            return self.repository.get_parents(self.hash)
        else:
            return None

    @property
    def local(self):
        return self[1]

    @property
    def hash(self):
        return self[2]

    @property
    def shorthash(self):
        return self.hash[:self.SHORT_HASH_COUNT]

    @property
    def tags(self):
        return self[3]

    @property
    def branch(self):
        if not self[4]:
            return self.branches
        return self[4]

    @property
    def branches(self):
        if not self._branches:
            self._branches = self.repository.get_changeset_branches(self)
        return self._branches

    @property
    def author(self):
        return self[5]

    @property
    def desc(self):
        return self[6]

    @property
    def timestamp(self):
        return self[7]

    def get_ancestor(self, changeset):
        if self.repository:
            return self.repository.get_ancestor(self, changeset)
        else:
            return None

    def create_branch(self, name):
        return self.repository.branch(name)

    def create_tag(self, name, message):
        return self.repository.tag(name, self.hash, message)
