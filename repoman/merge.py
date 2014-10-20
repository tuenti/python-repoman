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


class MergeStrategy(object):
    """
    Defines an strategy to perform a merge operation, its arguments are the
    same as the ones of the merge method, plus an instance of
    repoman.Repository.
    """
    def __init__(self, repository, local_branch=None, other_rev=None,
                 other_branch_name=None):
        self.repository = repository
        self.local_branch = local_branch
        self.other_rev = other_rev
        self.other_branch_name = other_branch_name

    def perform(self):
        """
        Performs the merge itself, applying the changes in the files it
        possible and raising in case of conflicts, this operation should leave
        the Repository object in a state with enough information to abort the
        merge.
        """
        raise NotImplementedError("Abstract method")

    def abort(self):
        """
        Resets the repository to the state before the perform.
        """
        raise NotImplementedError("Abstract method")

    def commit(self):
        """
        Writes the final commit if proceeds and returns it.
        """
        raise NotImplementedError("Abstract method")
