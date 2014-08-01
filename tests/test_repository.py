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

try:
    import unittest2 as unittest
except ImportError:
    import unittest
import tempfile
import os
import shutil

from repoman.hg import hglibext as hglib
from repoman.hg.repository import Repository


class TestRepository(unittest.TestCase):

    def setUp(self):
        # Create execution path
        self.environment_path = tempfile.mkdtemp()
        self.main_repo = self.create_repo(self.environment_path)

    def tearDown(self):
        shutil.rmtree(self.environment_path)

    def create_repo(self, path, branch_name='integration', repo_name=None):
        if not repo_name:
            repo_name = "tuenti-ng"
        full_path = os.path.join(path, repo_name)
        os.mkdir(full_path)
        hglib.init(full_path)
        repo = hglib.open(full_path)
        repo.branch(branch_name)
        commits = ['initial commit', 'second commit', 'third commit']
        files = ['f1', 'f2', 'f3', 'f4']
        self.commit_in_repo(full_path, files, commits)
        repo.close()
        return full_path

    def commit_in_repo(self, repo_path, files, commits):
        repo = hglib.open(repo_path)
        rev = None
        for commit in commits:
            for file_name in files:
                file = open(os.path.join(repo_path, file_name), "a")
                file.write("%s in %s\n" % (commit, file_name))
                file.close()
                repo.add(os.path.join(repo_path, file_name))
            rev = repo.commit(message=commit, user="Test user")
        repo.close()
        return rev

    def clone_repo(self, where_to, repo_path, revision="tip"):
        repo = hglib.open(repo_path)
        repo.clone(source=repo_path, dest=where_to, revrange=revision)

    def disable_hook(self, repo_path, hook):
        hgrc_path = os.path.join(repo_path, ".hg/hgrc")
        if os.path.exists(hgrc_path):
            hgrc = open(hgrc_path, 'a')
            hgrc.write("[hooks]\n%s=" % hook)
            hgrc.close()

    def test_full_merge_and_push(self):
        repo_path = os.path.join(self.environment_path, "mergepush")
        self.clone_repo(repo_path, self.main_repo, revision="tip")
        base_branch = "integration"
        origin = self.main_repo
        destination = 'http://push.fake'
        repo = hglib.open(repo_path)
        repo.branch(base_branch)
        # Let's merge with an ancestor so the push is not performed
        hash = 1

        repo = Repository(self.main_repo)
        repo.full_merge_and_push(base_branch, hash, 'fake_branch',
                                 origin, destination)
