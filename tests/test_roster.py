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

import tempfile
import os

from datetime import timedelta

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from repoman.roster import Roster, Clone, RosterError, MaxClonesLimitReached


def clone_mother(**kwargs):
    return Clone(
        kwargs.get('path', u'/test'),
        kwargs.get('status', Clone.FREE),
        kwargs.get('task', u'1'),
        kwargs.get('task_name', u'testing'),
        kwargs.get('timestamp', u'0'))


class TestRoster(unittest.TestCase):
    def setUp(self):
        self.roster = Roster(':memory:')

    def test_update(self):
        self.roster['/test'] = clone_mother(path='/test', status=Clone.INUSE)
        res = clone_mother(path='/test', status=Clone.INUSE)
        self.assertTrue(res.__eq__(self.roster['/test']))

    def test_delete(self):
        self.roster['/test1'] = clone_mother(status=Clone.INUSE)
        self.roster['/test2'] = clone_mother(status=Clone.INUSE)
        self.roster.clear()
        self.assertEquals(0, len(self.roster))

    def test_missing(self):
        self.assertRaises(KeyError, lambda x: self.roster[x], '/test')

    def test_fail_to_reserve_without_clones(self):
        self.assertRaises(RosterError, self.roster.reserve_clone, '1', 'test')

    def test_fail_to_reserve_without_free_clones(self):
        self.roster['/test'] = clone_mother(status=Clone.INUSE)
        self.assertRaises(RosterError, self.roster.reserve_clone, '1', 'test')

    def test_get_free(self):
        r1 = clone_mother(status=Clone.INUSE)
        r2 = clone_mother(status=Clone.FREE)
        self.roster['/test1'] = r1
        self.roster['/test2'] = r2
        r2.status = Clone.INUSE
        self.assertEquals(r2, self.roster.reserve_clone('1', 'test'))

    def test_clone_str(self):
        r1 = clone_mother(status=Clone.INUSE)
        self.assertEquals(r1.__str__(), str(r1.__dict__))
        self.assertEquals(r1.__repr__(), str(r1.__dict__))

    def test_free_clone(self):
        r1 = clone_mother(status=Clone.INUSE, task='1')
        r2 = clone_mother(status=Clone.FREE, task='2')
        r3 = clone_mother(status=Clone.INUSE, task='2')

        self.roster['/test1'] = r1
        self.roster['/test2'] = r2
        self.roster['/test3'] = r3
        self.roster.free_clone(r1, '1')
        r1 = self.roster['/test1']
        self.assertEquals(Clone.FREE, r1.status)
        # Check cannot remove elements from the roster not owned.
        self.assertRaises(RosterError, self.roster.free_clone, r3, 1)

    def test_fail_to_modify_others_clone(self):
        r1 = clone_mother(path='/test', status=Clone.INUSE, task='2')
        r2 = clone_mother(path='/test', status=Clone.INUSE, task='1')
        self.roster['/test'] = r1

        def assign(x, y):
            self.roster[x] = y
        self.assertRaises(RosterError, assign, '/test', r2)

    def test_add(self):
        self.roster.add('/test', 1, 'test')
        self.assertIn('/test', self.roster)
        self.assertRaises(RosterError, self.roster.add, '/test', 1, 'test')
        r1 = self.roster.add('/test1', 1, 'test')
        self.assertIn(r1, self.roster.values())

    def test_iter(self):
        self.assertListEqual([], list(self.roster))
        r1 = self.roster.add('/test1', 1, 'test')
        r2 = self.roster.add('/test2', 1, 'test')
        r3 = self.roster.add('/test3', 1, 'test')
        repo_list = [u'/test1', u'/test2', u'/test3']
        self.assertListEqual(repo_list, list(self.roster))
        self.assertListEqual([r1, r2, r3], self.roster.values())

    def test_get_available(self):
        self.assertListEqual([], self.roster.get_available())
        r1 = self.roster.add('/test1', u'1', 'test')
        r2 = self.roster.add('/test2', u'2', 'test')
        r3 = self.roster.add('/test3', u'1', 'test')
        self.assertListEqual([], self.roster.get_available())
        self.roster.free_clone(r1, u'1')
        self.roster.free_clone(r2, u'2')
        self.roster.free_clone(r3, u'1')
        self.assertListEqual([r1, r2, r3], self.roster.get_available())

    def test_get_not_available(self):
        self.assertListEqual([], self.roster.get_not_available())
        self.roster.add('/test', u'1', 'test')
        r = self.roster['/test']
        self.assertListEqual([r], self.roster.get_not_available())
        self.roster.free_clone(r, u'1')
        self.assertListEqual([], self.roster.get_not_available())

    def test_get_single(self):
        self.assertListEqual([], self.roster.get_available())
        r1 = self.roster.add('/test1', u'1', 'test')
        self.assertEquals(r1, self.roster['/test1'])
        r2 = self.roster.add('/test2', u'1', 'test')
        self.assertEquals(r2, self.roster['/test2'])

    def test_add_limit(self):
        # tests the limit imposed to the creation of clones
        roster = Roster(':memory:', max_clones=1)
        roster.add('/test1', 1, 'test')
        self.assertIn('/test1', roster)
        self.assertRaises(
            MaxClonesLimitReached, roster.add, '/test2', 1, 'test')

    def test_free_clone_by_timeout(self):
        timeout = timedelta(seconds=1)
        initial_time = 0.0

        roster = Roster(':memory:', clone_timeout=timeout)
        roster._get_time_ = lambda: initial_time

        r1 = clone_mother(status=Clone.INUSE, task='1')
        r2 = clone_mother(status=Clone.FREE, task='2')
        r3 = clone_mother(status=Clone.INUSE, task='2')
        roster['/test1'] = r1
        roster['/test2'] = r2
        roster['/test3'] = r3

        self.assertListEqual([], roster._get_old_clones_())

        roster._get_time_ = lambda: initial_time + timeout.seconds + 1
        self.assertGreater(len(roster._get_old_clones_()), 0)

        roster._clean_old_clones()
        self.assertListEqual([], roster._get_old_clones_())

    def test_multiple_rosters_persistence(self):
        fd, database_path = tempfile.mkstemp()
        try:
            roster1 = Roster(database_path)
            roster2 = Roster(database_path)
            r1 = clone_mother(task='1', status=Clone.INUSE)
            r2 = clone_mother(task='2')

            roster1['/test1'] = r1

            def assign(roster, x, y):
                roster[x] = y
            self.assertRaises(RosterError, assign, roster2, '/test1', r2)

            roster1['/test2'] = r2
            roster2.reserve_clone('2', 'test2')
            self.assertRaises(RosterError, roster1.reserve_clone, '1', 'test1')
        finally:
            os.remove(database_path)
