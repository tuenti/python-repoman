#!/usr/bin/env python
"""
Copyright 2014 Tuenti Technologies S.L.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from repoman.commitmessage import CommitMessage, DefaultCommitMessageBuilder


class TestCommitMessage(unittest.TestCase):
    def testCommitMessage(self):
        message = "A message with %(something)s"
        values = {'something': 'foo'}
        commit_message = CommitMessage(message, values)
        self.assertEquals(str(commit_message), message % values)

    def testCloseBranchMessage(self):
        builder = DefaultCommitMessageBuilder()
        str(builder.close_branch(branch='foo'))

    def testMergeMessage(self):
        builder = DefaultCommitMessageBuilder()
        self.assertTrue(bool(str(builder.merge())))

    def testMergeMessageWithArguments(self):
        builder = DefaultCommitMessageBuilder()
        self.assertTrue('foo' in str(builder.merge(other_branch='foo')))
        message = str(builder.merge(local_branch='foo',
                                    local_revision='fabada',
                                    other_branch='bar',
                                    other_revision='deadbeef'))
        self.assertTrue('foo' in message)
        self.assertTrue('fabada' in message)
        self.assertTrue('bar' in message)
        self.assertTrue('deadbeef' in message)

    def testBuilderOverride(self):
        class MyCustomBuilder(DefaultCommitMessageBuilder):
            def __init__(self, prefix):
                self.prefix = prefix

            def commit_message(self, message, values={}):
                return CommitMessage("%s %s" % (self.prefix, message), values)

        label = "LABEL:"
        branch_name = 'foo'
        builder = MyCustomBuilder(prefix=label)
        message = builder.close_branch(branch=branch_name)
        self.assertTrue(str(message).startswith(label))
