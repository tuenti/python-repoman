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
import pygit2
import sh
from repoman.git.depot_operations import DepotOperations
from repoman.git import pygitext

SELF_DIRECTORY_PATH = os.path.dirname(__file__)
FIXTURE_PATH = 'fixtures'


class TestGitDepotOperations(unittest.TestCase):

    def setUp(self):
        # Create execution path
        self.environment_path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.environment_path)

    def create_repo(self, name):
        return pygit2.init_repository(
            os.path.join(self.environment_path, name))

    def add_content_to_repo(self, fixture, name):
        pygitext.clone(
            os.path.join(SELF_DIRECTORY_PATH, fixture),
            os.path.join(self.environment_path, name),
            bare=True)

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

            # Note: the hg implementations is way less "intelligent"
            self.assertFalse(dcvs.is_a_depot(main_test_dir))

        finally:
            shutil.rmtree(main_test_dir)

    def test_check_changeset_availability(self):

        # Creates a repo, import the fixture bundle
        #   Fixture bundle:
        #   Two changesets inside:
        #
        # commit 52109e71fd7f16cb366acfcbb140d6d7f2fc50c9
        # Author: Jose Plana <jplana@tuenti.com>
        # Date:   Thu Nov 14 17:50:49 2013 +0100
        #
        #    Second changeset
        #
        # diff --git a/test2.txt b/test2.txt
        # new file mode 100644
        # index 0000000..e69de29
        #
        # commit e3b1fc907ea8b3482e29eb91520c0e2eee2b4cdb
        # Author: Jose Plana <jplana@tuenti.com>
        # Date:   Thu Nov 14 17:50:29 2013 +0100
        #
        #    First changeset
        #
        # diff --git a/test1.txt b/test1.txt
        # new file mode 100644
        # index 0000000..e69de29
        #

        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-1.git.bundle'), 'repo1')
        dcvs = DepotOperations()

        # It is not there
        self.assertEquals(
            ['52109e71fd7f16cb366acfcbb140d6d7f2fc50c9'],
            dcvs.check_changeset_availability(
                os.path.join(self.environment_path, 'repo1'),
                ['52109e71fd7f16cb366acfcbb140d6d7f2fc50c9']))

    def test_master_grab_changesets(self):
        # Grabs branch from a "remote" depot.

        # Remote repository
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-2.git.bundle'), 'remote')

        dcvs = DepotOperations()

        dcvs.init_depot(
            os.path.join(self.environment_path, 'master'),
            parent=None,
            source=os.path.join(self.environment_path, 'remote'))

        # Changeset both there
        self.assertEquals(
            True, dcvs.grab_changesets(
                os.path.join(self.environment_path, 'master'),
                os.path.join(self.environment_path, 'remote'),
                ['my-branch1']))

        # Check availability
        sh.git('log', '4632aa0b30c65cd1c6ec978d2905836ae65509ed',
               _cwd=os.path.join(self.environment_path, 'master'))

        # Changesets not there
        self.assertTrue(
            dcvs.grab_changesets(
                os.path.join(self.environment_path, 'master'),
                os.path.join(self.environment_path, 'remote'),
                ['c377d40d21153bdcc4ec0b24bba48af3899fcc7x',
                    'b93d349f220d892047817f7ab29b2e8bfc5569bx']))

        # TODO: Optimize this so we fetch only specific refspecs
        # (and don't fetch all of them)
        #
        # Check availability (not fetched)
        # self.assertEquals(['b0955744aa0b796a2b810ee7b9a79fcbd43849b9'],
        #                  dcvs.check_changeset_availability(
        #                      os.path.join(self.environment_path, 'master'),
        #                      ['b0955744aa0b796a2b810ee7b9a79fcbd43849b9']))

    def test_request_refresh_git(self):
        dcvs = DepotOperations()

        # Remote repository
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-2.git.bundle'),
            'remote')

        # Master cache
        master = dcvs.init_depot(
            os.path.join(self.environment_path, 'master'),
            parent=None,
            source=os.path.join(self.environment_path, 'remote'))

        # Workspace depot
        workspace1 = dcvs.init_depot(
            os.path.join(self.environment_path, 'workspace1'),
            parent=master,
            source=os.path.join(self.environment_path, 'master'))

        self.assertTrue(workspace1.request_refresh({
            os.path.join(self.environment_path, 'remote'): ['my-branch1']}))
