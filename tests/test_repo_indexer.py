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

import mox

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from repoman.repo_indexer import MultiRepoIndexer


class FakeRIClass(object):

    def __init__(self, test, url, user, passwd):
        pass


class TestRepoIndexer(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_register_indexer(self):
        rind_matrix = {'id5': 'test2',
                       'id7': 'test1',
                       'id6': 'test3'}

        repo_indexer = MultiRepoIndexer(rind_matrix)
        fake_class_name = 'tests.test_repo_indexer.FakeRIClass'
        repo_indexer.register_indexer(
            10, fake_class_name, 'id5', ('r', 'u', 'p'))
        repo_indexer.register_indexer(
            13, fake_class_name, 'id7', ('r', 'u', 'p'))
        repo_indexer.register_indexer(
            1, fake_class_name, 'id6', ('r', 'u', 'p'))

        res = repo_indexer._indexers
        ordered_keys = iter([1, 10, 13])
        for i in res.items():
            self.assertEquals(i[0], ordered_keys.next())

    def test_get_branches_first_bad_second_good(self):
        expected = ['a', 'b']

        fake_indexer_bad = self.mox.CreateMockAnything()
        fake_indexer_bad.get_branches(2).AndRaise(Exception('test'))
        fake_indexer_good = self.mox.CreateMockAnything()
        fake_indexer_good.get_branches(2).AndReturn(expected)

        fake_indexers = {
            1: fake_indexer_bad,
            2: fake_indexer_good
        }

        self.mox.ReplayAll()

        repo_indexer = MultiRepoIndexer(None)
        repo_indexer._indexers = fake_indexers

        res = repo_indexer.get_branches(limit=2)

        self.assertEquals(res, expected)

        self.mox.VerifyAll()
