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


class CommitMessage(object):

    def __init__(self, message, values={}):
        self.message = message
        self.values = values

    def __str__(self):
        return self.message % self.values


class DefaultCommitMessageBuilder(object):
    CLOSE_BRANCH = "Closing branch %(branch)s"
    MERGE = "Merging %(other_branch)s@%(other_revision)s into " +\
        "%(local_branch)s@%(local_revision)s"

    def commit_message(self, message, values={}):
        return CommitMessage(message, values)

    def commit(self, message, values={}):
        if isinstance(message, CommitMessage):
            return message
        else:
            return self.commit_message(message)

    def close_branch(self, branch):
        return self.commit_message(self.CLOSE_BRANCH, {
            'branch': branch
        })

    def merge(self, local_branch=None, local_revision=None, other_branch=None,
              other_revision=None):
        return self.commit_message(self.MERGE, {
            'local_branch': local_branch or "",
            'local_revision': local_revision or "",
            'other_branch': other_branch or "",
            'other_revision': other_revision or "",
        })
