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
import shutil
import sh

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from repoman.changeset import Changeset
from repoman.git.repository import Repository, GitCmd

FIXTURE_PATH = 'fixtures'
SELF_DIRECTORY_PATH = os.path.dirname(__file__)


class TestGitChangeset(unittest.TestCase):

    def setUp(self):
        self.environment_path = tempfile.mkdtemp()
        fixture_path = os.path.join(FIXTURE_PATH, 'fixture-2.git.bundle')
        self.add_content_to_repo(fixture_path, 'remote')

    def tearDown(self):
        shutil.rmtree(self.environment_path)

    def create_repo(self, name):
        sh.git("init",
            os.path.join(self.environment_path, name))

    def add_content_to_repo(self, fixture, name):
        sh.git("clone",
            os.path.join(SELF_DIRECTORY_PATH, fixture),
            os.path.join(self.environment_path, name),
            bare=True)

    def test_init(self):
        git = GitCmd(os.path.join(self.environment_path, 'remote'))
        gitrepo = Repository(os.path.join(self.environment_path, 'remote'))
        gitcs = gitrepo[git('rev-parse', 'HEAD')]
        self.assertEquals(gitcs.author, "Jose Plana")
        self.assertEquals(
            gitcs.hash, "52109e71fd7f16cb366acfcbb140d6d7f2fc50c9")
        self.assertEquals(
            gitcs.desc.rstrip('\n'), "Second changeset".rstrip('\n'))
        self.assertFalse(gitcs.merge)
        print(gitrepo.get_parents("52109e71fd7f16cb366acfcbb140d6d7f2fc50c9"))
        self.assertEquals(
            gitcs.parents[0].hash, "e3b1fc907ea8b3482e29eb91520c0e2eee2b4cdb")

    def test_create_branch(self):
        non_bare_repo_path = os.path.join(
            self.environment_path, 'remote-non-bare')
        sh.git("clone",
            os.path.join(self.environment_path, 'remote'),
            non_bare_repo_path,
        )
        git = GitCmd(non_bare_repo_path)
        gitrepo = Repository(non_bare_repo_path)
        gitcs = gitrepo[git('rev-parse', 'HEAD')]
        branch = gitcs.create_branch('fakebranch')
        self.assertEquals(branch.get_changeset(), gitrepo.tip())
        self.assertEquals(
            'fakebranch', git('rev-parse', '--abbrev-ref', 'fakebranch'))

    def test___str__(self):
        git = GitCmd(os.path.join(self.environment_path, 'remote'))
        gitrepo = Repository(os.path.join(self.environment_path, 'remote'))
        gitcs = gitrepo[git('rev-parse', 'HEAD')]
        self.assertEquals(
            gitcs.__str__(),
            git('rev-parse', 'HEAD')[:Changeset.SHORT_HASH_COUNT])
