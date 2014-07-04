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
import shutil
import os
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from repoman.depot_manager import DepotManager
from repoman.roster import Clone
from repoman.signature import Signature

FIXTURE_PATH = 'fixtures'
SELF_DIRECTORY_PATH = os.path.dirname(__file__)


class AbstractTestDepotManager(object):
    REPO_KIND = None

    def setUp(self):
        # Create execution path
        self.enviroment_path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.enviroment_path)

    def test_give_me_depot(self):
        # Check we can always reserve a new repo.
        rman = DepotManager(
            main_workspace=self.enviroment_path, repo_kind=self.REPO_KIND)
        new_clone = rman.give_me_depot('1', 'bla', {}, rman.main_cache_path)
        self.assertIsNotNone(new_clone)
        self.assertEquals(Clone.INUSE, rman.roster[new_clone.path].status)

    def test_free_depot(self):
        # Check we can free a reserved clone.
        rman = DepotManager(
            main_workspace=self.enviroment_path, repo_kind=self.REPO_KIND)
        # Reserve clone
        repo = rman.give_me_depot('1', 'bla', {}, rman.main_cache_path)
        self.assertIsNotNone(repo)
        self.assertEquals(Clone.INUSE, rman.roster[repo.path].status)

        # Free the repo.
        rman.free_depot(repo, '1')
        self.assertIn(repo.path, rman.roster)
        self.assertEquals(Clone.FREE, rman.roster[repo.path].status)

    @staticmethod
    def _add_file(repo, file_name):
        with open(os.path.join(repo.path, file_name), 'w+') as f:
            f.write('something\n')
        repo.add([file_name])

    @staticmethod
    def _get_tag_names(tags):
        return list(tags)

    @staticmethod
    def _get_branch_names(branches):
        return [branch.name for branch in branches]

    def test_free_depot_with_new_references(self):
        rman = DepotManager(
            main_workspace=self.enviroment_path, repo_kind=self.REPO_KIND)
        depot = rman.give_me_depot('1', 'bla', {}, rman.main_cache_path)
        signature = Signature(user='test', email='test@example.com')

        new_tag = 'new_tag'
        new_branch = 'new_branch'

        # Work on the repository and free it, it should be cleared
        self._add_file(depot.repository, 'foo')
        depot.repository.commit("Initial message", signature=signature)
        depot.repository.branch(new_branch)
        self._add_file(depot.repository, 'bar')
        depot.repository.commit("Other commit", signature=signature)
        depot.repository.tag(new_tag)
        self.assertIn(
            new_tag,
            self._get_tag_names(depot.repository.tags()))
        self.assertIn(
            new_branch,
            self._get_branch_names(depot.repository.get_branches()))
        rman.free_depot(depot, '1')

        # Work again with the same repository, and check that previous branches
        # and tags are not there
        depot = rman.give_me_depot('1', 'bla', {}, rman.main_cache_path)
        self._add_file(depot.repository, 'baz')
        depot.repository.commit("Initial message", signature=signature)
        self.assertNotIn(
            new_tag,
            self._get_tag_names(depot.repository.tags()))
        self.assertNotIn(
            new_branch,
            self._get_branch_names(depot.repository.get_branches()))
        rman.free_depot(depot, '1')

        # And check again that the repository can be requested and released
        depot = rman.give_me_depot('1', 'bla', {}, rman.main_cache_path)
        self.assertNotIn(
            new_tag,
            self._get_tag_names(depot.repository.tags()))
        self.assertNotIn(
            new_branch,
            self._get_branch_names(depot.repository.get_branches()))
        rman.free_depot(depot, '1')

    def test_list_clones(self):
        # Check if we can retrieve a list of reserved + non_reserved scm.
        rman = DepotManager(
            main_workspace=self.enviroment_path, repo_kind=self.REPO_KIND)
        self.assertListEqual([], rman.roster.values())
        repo = rman.give_me_depot('1', 'bla', {}, rman.main_cache_path)
        self.assertListEqual([rman.roster[repo.path]], rman.roster.values())

    def test_available_clones(self):
        # Check if we can retrieve a list of non_reserved scm.
        rman = DepotManager(
            main_workspace=self.enviroment_path, repo_kind=self.REPO_KIND)
        self.assertSequenceEqual([], rman.roster.get_available())
        repo = rman.give_me_depot('1', 'bla', {}, rman.main_cache_path)
        self.assertIsNotNone(repo)
        # Free the repo.
        clon = [clone for clone in rman.roster.get_not_available()
                if clone.path == repo.path][0]
        rman.free_depot(clon, '1')
        repo_clon = [
            clone for clone in rman.roster.get_available()
            if clone.path == repo.path
        ][0]

        self.assertSequenceEqual([repo_clon], rman.roster.get_available())
        self.assertEquals(
            repo_clon, rman.get_available_clone(repo_clon.path))
        self.assertIsNone(rman.get_not_available_clone(repo_clon.path))

    @staticmethod
    def mock_lock(path):
        raise NotImplemented()

    def test_lock_cleanup(self):
        rman = DepotManager(
            main_workspace=self.enviroment_path, repo_kind=self.REPO_KIND)

        # Simulate an unlocked repository, rman.free_depot is not used because
        # it calls repository operations that can depend on the locks
        depot = rman.give_me_depot('1', 'bla')
        self.mock_lock(depot.path)
        rman.roster.free_clone(rman.get_not_available_clone(depot.path), '1')

        depot = rman.give_me_depot('1', 'bla')
        self._add_file(depot.repository, 'foo')


class TestGitDepotManager(AbstractTestDepotManager, unittest.TestCase):
    REPO_KIND = 'git'

    @staticmethod
    def mock_lock(path):
        index_lock_path = os.path.join(path, '.git/index.lock')
        open(index_lock_path, 'w').close()


class TestHgDepotManager(AbstractTestDepotManager, unittest.TestCase):
    REPO_KIND = 'hg'

    @staticmethod
    def _get_tag_names(tags):
        for tag in tags:
            yield tag[0]

    @staticmethod
    def mock_lock(path):
        wlock_path = os.path.join(path, '.hg/wlock')
        lock_path = os.path.join(path, '.hg/store/lock')
        for path in (wlock_path, lock_path):
            open(path, 'w').close()
