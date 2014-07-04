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

import os
import tempfile
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import shutil

from repoman.hg.depot_operations import DepotOperations
from repoman.hg import hglibext as hglib

SELF_DIRECTORY_PATH = os.path.dirname(__file__)
FIXTURE_PATH = 'fixtures'


class TestHgDepotOperations(unittest.TestCase):

    def setUp(self):
        # Create execution path
        self.environment_path = tempfile.mkdtemp()

    def tearDown(self):
        pass

    def create_repo(self, name):
        return hglib.init(os.path.join(self.environment_path, name))

    def add_content_to_repo(self, fixture, name):
        repository_path = os.path.join(self.environment_path, name)
        fixture_path = os.path.join(SELF_DIRECTORY_PATH, fixture)
        with hglib.open(repository_path) as client:
            client.unbundle(fixture_path)

    def test_check_is_a_repo(self):
        dcvs = DepotOperations()

        # Non existent path.
        self.assertFalse(dcvs.is_a_depot('/tmp/nonexistentcrazypath'))

        main_test_dir = os.path.join(self.environment_path, 'crazy_path')
        if not os.path.isdir(main_test_dir):
            os.mkdir(main_test_dir)

        try:
            # Existent directory but not a repository.
            self.assertFalse(dcvs.is_a_depot(main_test_dir))

            # Existent directory with another directory inside called .hg
            os.mkdir(os.path.join(main_test_dir, '.hg'))
            self.assertTrue(dcvs.is_a_depot(main_test_dir))

        finally:
            shutil.rmtree(main_test_dir)

    def test_check_changeset_availability(self):

        # Creates a repo, import the fixture bundle
        #   Fixture bundle:
        #   Two changesets inside:
        #
        #
        # changeset:   1:c377d40d21153bdcc4ec0b24bba48af3899fcc7c
        # tag:         tip
        # phase:       draft
        # parent:      0:b93d349f220d892047817f7ab29b2e8bfc5569ba
        # parent:      -1:0000000000000000000000000000000000000000
        # manifest:    1:c82de0153e73524cbb6643c59e68f8b16363f2a8
        # user:        Jose Plana <jplana@tuenti.com>
        # date:        Tue Jul 17 21:05:01 2012 +0200
        # files+:      test2.txt
        # extra:       branch=default
        # description:
        # Second changeset
        #
        #
        # changeset:   0:b93d349f220d892047817f7ab29b2e8bfc5569ba
        # phase:       draft
        # parent:      -1:0000000000000000000000000000000000000000
        # parent:      -1:0000000000000000000000000000000000000000
        # manifest:    0:826ca3493fad5ba7a0e9f51a0d5017ace8265fb8
        # user:        Jose Plana <jplana@tuenti.com>
        # date:        Tue Jul 17 21:04:34 2012 +0200
        # files+:      test1.txt
        # extra:       branch=default
        # description:
        # First changeset
        # tag:         tip
        # user:        Jose Plana <jplana@tuenti.com>
        # date:        Tue Jul 17 21:05:01 2012 +0200
        # summary:     Second changeset

        self.create_repo('repo1')
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-1.hg.bundle'),
            'repo1')
        dcvs = DepotOperations()

        # It is there
        self.assertEquals(
            [], dcvs.check_changeset_availability(
                os.path.join(self.environment_path, 'repo1'),
                ['c377d40d21153bdcc4ec0b24bba48af3899fcc7c']))

        # It is not there
        self.assertEquals(
            ['5638868af469d1ba1dba2d3e1dc77e677c6f78ae'],
            dcvs.check_changeset_availability(
                os.path.join(self.environment_path, 'repo1'),
                ['5638868af469d1ba1dba2d3e1dc77e677c6f78ae']))

        # It is there (multiple changesets)
        self.assertEquals(
            [], dcvs.check_changeset_availability(
                os.path.join(self.environment_path, 'repo1'),
                ['c377d40d21153bdcc4ec0b24bba48af3899fcc7c',
                 'b93d349f220d892047817f7ab29b2e8bfc5569ba']))

        # It is not there (multiple changesets one is excluded)
        self.assertEquals(
            ['5638868af469d1ba1dba2d3e1dc77e677c6f78ae'],
            dcvs.check_changeset_availability(
                os.path.join(self.environment_path, 'repo1'),
                ['5638868af469d1ba1dba2d3e1dc77e677c6f78ae',
                 'c377d40d21153bdcc4ec0b24bba48af3899fcc7c',
                 'b93d349f220d892047817f7ab29b2e8bfc5569ba']))

    def test_grab_changesets(self):

        # Grabs a couple of changesets from a "remote" depot.

        self.create_repo('repo2')
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-1.hg.bundle'),
            'repo2')
        self.create_repo('repo3')

        dcvs = DepotOperations()

        # Changeset both there
        self.assertTrue(
            dcvs.grab_changesets(
                os.path.join(self.environment_path, 'repo3'),
                os.path.join(self.environment_path, 'repo2'),
                ['c377d40d21153bdcc4ec0b24bba48af3899fcc7c',
                    'b93d349f220d892047817f7ab29b2e8bfc5569ba']))

        # Check availability
        self.assertEquals(
            [], dcvs.check_changeset_availability(
                os.path.join(self.environment_path, 'repo3'),
                ['c377d40d21153bdcc4ec0b24bba48af3899fcc7c',
                 'b93d349f220d892047817f7ab29b2e8bfc5569ba']))

        # Changesets not there
        self.assertFalse(
            dcvs.grab_changesets(
                os.path.join(self.environment_path, 'repo3'),
                os.path.join(self.environment_path, 'repo2'),
                ['c377d40d21153bdcc4ec0b24bba48af3899fcc7x',
                    'b93d349f220d892047817f7ab29b2e8bfc5569bx']))
