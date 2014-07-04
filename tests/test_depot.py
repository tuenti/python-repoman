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

import tempfile
import unittest
import shutil

import mox

from repoman.depot import Depot
from repoman.depot_operations import DepotOperations


class TestDepot(unittest.TestCase):

    def setUp(self):
        # Create execution path
        self.environment_path = tempfile.mkdtemp()
        self.child_path = tempfile.mkdtemp()
        self.mox = mox.Mox()

        self.dvcs = self.mox.CreateMock(DepotOperations())
        self.depot = Depot(self.environment_path, None, self.dvcs)

    def tearDown(self):
        shutil.rmtree(self.environment_path)
        shutil.rmtree(self.child_path)
        self.mox.UnsetStubs()
        self.mox.VerifyAll()

    def test_grab_changesets_to(self):
        # Mock the dvcs operations
        self.mox.StubOutWithMock(self.depot, 'grab_changesets_from_upstream')

        # Record behavior.
        reqs = {
            'a': range(1, 6),
            'b': range(1, 8),
        }
        self.depot.grab_changesets_from_upstream(reqs)

        # Replay
        self.mox.ReplayAll()
        # Test
        self.depot._grab_changesets_to_(reqs, '/pepe')

    def test_filter(self):
        # Mock the dvcs operations
        self.mox.StubOutWithMock(self.dvcs, 'check_changeset_availability')

        # Record
        self.dvcs.check_changeset_availability(
            self.environment_path,
            range(1, 6)).AndReturn(range(1, 6))

        self.dvcs.check_changeset_availability(
            self.environment_path,
            range(8, 13)).AndReturn([8])

        # Replay
        self.mox.ReplayAll()

        # Test
        reqs = {
            'a': range(1, 6),
            'b': range(8, 13),
        }

        self.assertEquals(
            {'a': range(1, 6), 'b': [8]},
            self.depot._filter_missing_changesets(reqs))

    def test_grab_changesets_from_upstream(self):
        # Record
        self.dvcs.grab_changesets(
            self.environment_path, 'a', range(1, 6)
        ).InAnyOrder().AndReturn(True)
        self.dvcs.grab_changesets(
            self.environment_path, 'b', range(8, 13)
        ).InAnyOrder().AndReturn(True)
        self.dvcs.grab_changesets(
            self.environment_path, 'a', range(1, 6)
        ).InAnyOrder().AndReturn(False)

        # Replay
        self.mox.ReplayAll()

        # Test
        reqs = {'a': range(1, 6), 'b': range(8, 13)}
        self.depot.grab_changesets_from_upstream(reqs)
        self.assertFalse(self.depot.grab_changesets_from_upstream(reqs))

    def test_grab_changesets_from_upstream_cache(self):
        reqs1 = range(1, 6)
        reqs2 = range(8, 13)
        reqs = reqs = {'a': reqs1, 'b': reqs2}
        # Mock the dvcs operations
        child_depot = Depot(self.child_path, self.depot, self.dvcs)

        # Record
        self.mox.StubOutWithMock(self.depot, '_grab_changesets_to_')
        self.depot._grab_changesets_to_(
            reqs, self.child_path).InAnyOrder().AndReturn(True)

        # Replay
        self.mox.ReplayAll()

        # Test
        self.assertTrue(child_depot.grab_changesets_from_upstream(reqs))
