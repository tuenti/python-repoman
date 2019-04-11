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

import os
import tempfile
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import shutil
import sh
from repoman.git.depot_operations import DepotOperations

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
        sh.git('clone',
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

        missing_changeset = '52109e71fd7f16cb366acfcbb140d6d7f2fc50c8'

        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-1.git.bundle'), 'repo1')
        dcvs = DepotOperations()

        # It is there
        self.assertEquals(
            [],
            dcvs.check_changeset_availability(
                os.path.join(self.environment_path, 'repo1'),
                ['52109e71fd7f16cb366acfcbb140d6d7f2fc50c9']))

        # It is not there
        self.assertEquals(
            [missing_changeset],
            dcvs.check_changeset_availability(
                os.path.join(self.environment_path, 'repo1'),
                [missing_changeset]))

        # Missing branches and changesets
        self.assertEquals(
            ['missing_branch', missing_changeset, 'deadbeef'],
            dcvs.check_changeset_availability(
                os.path.join(self.environment_path, 'repo1'),
                ['missing_branch', missing_changeset, 'deadbeef']))


        # Multiple changesets
        self.assertEquals(
            [missing_changeset],
            dcvs.check_changeset_availability(
                os.path.join(self.environment_path, 'repo1'),
                [missing_changeset,
                 '52109e71fd7f16cb366acfcbb140d6d7f2fc50c9']))

        # All changesets
        self.assertEquals(
            [],
            dcvs.check_changeset_availability(
                os.path.join(self.environment_path, 'repo1'),
                [
                    'master',
                    'e3b1fc907ea8b3482e29eb91520c0e2eee2b4cdb',
                    '52109e71fd7f16cb366acfcbb140d6d7f2fc50c9',
                ]))

    def test_check_changeset_availability_on_workspace(self):
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

        # There are commands that can accept files and changesets,
        # check that we are not mixing files with changesets when checking
        # available changesets in working copies
        open(os.path.join(workspace1.path, 'deadbeef'), 'w').close()
        self.assertEquals(
            ['deadbeef'],
            dcvs.check_changeset_availability(workspace1.path, ['deadbeef']))

    def test_master_grab_changesets(self):
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
        self.assertFalse(
            dcvs.grab_changesets(
                os.path.join(self.environment_path, 'master'),
                os.path.join(self.environment_path, 'remote'),
                ['c377d40d21153bdcc4ec0b24bba48af3899fcc7x',
                    'b93d349f220d892047817f7ab29b2e8bfc5569bx']))

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

    def test_request_refresh_git_url_does_not_exist(self):
        dcvs = DepotOperations()

        # Remote repository
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-2.git.bundle'),
            'remote')

        # Master cache
        master = dcvs.init_depot(
            os.path.join(self.environment_path, 'master'),
            parent=None,
            source=os.path.join(self.environment_path, 'other-remote'))

        # Workspace depot
        workspace1 = dcvs.init_depot(
            os.path.join(self.environment_path, 'workspace1'),
            parent=master,
            source=os.path.join(self.environment_path, 'master'))

        self.assertRaises(
            sh.ErrorReturnCode,
            workspace1.request_refresh,
            {
                os.path.join(self.environment_path, 'other-remote'): ['master']
            }
        )

    def _test_request_refresh(self, f):
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

        f(workspace1)

        # Other remote repository with additional references
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-4.git.bundle'),
            'other')

        with self.assertRaises(sh.ErrorReturnCode):
            sh.git('rev-parse', 'newbranch', _cwd=workspace1.path)

        self.assertTrue(workspace1.request_refresh({
            os.path.join(self.environment_path, 'other'): ['newbranch']}))

        self.assertEquals(
            sh.git('rev-parse', 'newbranch', _cwd=workspace1.path).strip(),
            "a277468c9cc0088ba69e0a4b085822d067e360ff")

    def test_request_refresh_git_workspace_clean(self):
        self._test_request_refresh(lambda w: None)

    def test_request_refresh_git_dirty_workspace(self):
        def taint(workspace):
            f = open(os.path.join(workspace.path, 'test1.txt'), 'w')
            f.write('taint!')
            f.close()
        self._test_request_refresh(taint)

    def test_request_refresh_git_untracked_file(self):
        def untracked(workspace):
            f = open(os.path.join(workspace.path, 'untracked.txt'), 'w')
            f.write('untracked!')
            f.close()
        self._test_request_refresh(untracked)

    def test_request_refresh_git_detached_workspace(self):
        def detach(workspace):
            sh.git('checkout', detach=True, _cwd=workspace.path)
        self._test_request_refresh(detach)

    def test_request_refresh_git_all_dirty_workspace(self):
        def taint_all(workspace):
            f = open(os.path.join(workspace.path, 'test1.txt'), 'w')
            f.write('taint!')
            f.close()
            f = open(os.path.join(workspace.path, 'untracked.txt'), 'w')
            f.write('untracked!')
            f.close()
            sh.git('checkout', detach=True, _cwd=workspace.path)
        self._test_request_refresh(taint_all)

    def test_request_refresh_not_existing_reference(self):
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

        with self.assertRaises(sh.ErrorReturnCode):
            sh.git('rev-parse', 'notexists', _cwd=workspace1.path)

        self.assertFalse(workspace1.request_refresh({
            os.path.join(self.environment_path, 'remote'): ['notexists']}))
