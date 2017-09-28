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

from mox3 import mox
import os.path

from repoman.hg.hgwebapi import HGWebApi

SELF_DIRECTORY_PATH = os.path.dirname(__file__)
FIXTURES_PATH = os.path.join(SELF_DIRECTORY_PATH, 'fixtures')

with open(os.path.join(FIXTURES_PATH, 'hgwebapi_branches_output')) as fixture:
    BRANCHES_OUTPUT = fixture.read()

BRANCHES_EXPECTED = [
    line.split()[0] for line in BRANCHES_OUTPUT.splitlines()
    if line
]


class TestHGWebApi(unittest.TestCase):

    def setUp(self):
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()

    def _get_lines(self, data):
        return data.split('\n')

    def test_get_branches(self):
        opener_fake = self.mox.CreateMockAnything()
        lines = self._get_lines(BRANCHES_OUTPUT)
        data = self.mox.CreateMockAnything()
        data.readlines().AndReturn(lines)
        fake_url = 'http://fake.local/fake_repo/branches?style=raw'
        opener_fake.open(fake_url).AndReturn(data)

        self.mox.ReplayAll()
        hgweb = HGWebApi("http://fake.local", "user", password="123")
        hgweb._opener = opener_fake
        branches = hgweb.get_branches('fake_repo')
        branches = iter(branches)

        for exp_branch in BRANCHES_EXPECTED:
            self.assertEqual(branches.next(), exp_branch)

        self.mox.VerifyAll()

    def test_get_branches_with_limit(self):
        opener_fake = self.mox.CreateMockAnything()
        lines = self._get_lines(BRANCHES_OUTPUT)
        data = self.mox.CreateMockAnything()
        data.readlines().AndReturn(lines)
        fake_url = 'http://fake.local/fake_repo/branches?style=raw'
        opener_fake.open(fake_url).AndReturn(data)

        self.mox.ReplayAll()
        hgweb = HGWebApi("http://fake.local", "user", password="123")
        hgweb._opener = opener_fake
        branches = hgweb.get_branches('fake_repo', 6)
        branches = iter(branches)

        for exp_branch in BRANCHES_EXPECTED[:6]:
            self.assertEqual(branches.next(), exp_branch)

        self.mox.VerifyAll()
