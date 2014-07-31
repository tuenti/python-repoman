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

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from repoman.changeset import Changeset
from repoman.hg.repository import Repository
from repoman.hg import hglibext as hglib

FIXTURE_PATH = 'fixtures'


class TestChangeset(unittest.TestCase):

    def create_repo(self, name):
        return hglib.init(os.path.join(self.environment_path, name))

    def add_content_to_repo(self, fixture, name):
        repository_path = os.path.join(self.environment_path, name)
        with hglib.open(repository_path) as client:
            fixture_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), fixture)
            client.unbundle(fixture_path)

    def setUp(self):
        self.environment_path = tempfile.mkdtemp()
        self.create_repo('repo1')
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-1.hg.bundle'), 'repo1')

    def tearDown(self):
        shutil.rmtree(self.environment_path)

    def test_init(self):
        clon = hglib.open(os.path.join(self.environment_path, 'repo1'))
        hgrepo = Repository(os.path.join(self.environment_path, 'repo1'))
        hgcs = Changeset(hgrepo, clon.tip())
        clon.close()
        self.assertEquals(hgcs.author, "Jose Plana <jplana@tuenti.com>")
        self.assertEquals(
            hgcs.hash, "c377d40d21153bdcc4ec0b24bba48af3899fcc7c")
        self.assertEquals(hgcs.desc, "Second changeset")
        self.assertFalse(hgcs.merge)
        self.assertEquals(
            hgcs.parents[0].hash, "b93d349f220d892047817f7ab29b2e8bfc5569ba")

    def test_create_branch(self):
        clon = hglib.open(os.path.join(self.environment_path, 'repo1'))
        clon.update('default')
        hgrepo = Repository(os.path.join(self.environment_path, 'repo1'))
        hgcs = Changeset(hgrepo, clon.tip())
        branch = hgcs.create_branch('fakebranch')
        self.assertEquals(branch.get_changeset(), hgrepo.tip())
        self.assertEquals('fakebranch', clon.branch())
        clon.close()

    def test___str__(self):
        clon = hglib.open(os.path.join(self.environment_path, 'repo1'))
        clon.update('default')
        hgrepo = Repository(os.path.join(self.environment_path, 'repo1'))
        hgcs = Changeset(hgrepo, clon.tip())
        self.assertEquals(
            hgcs.__str__(), clon.tip().node[:Changeset.SHORT_HASH_COUNT])
