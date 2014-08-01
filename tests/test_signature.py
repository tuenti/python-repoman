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

import unittest

from repoman.signature import Signature
from repoman.repository import Repository


class TestRepository(Repository):
    def __init__(self, test_case, *args, **kwargs):
        super(TestRepository, self).__init__(repo_path='fake', *args, **kwargs)
        self.test_case = test_case
        self.expected_signature = None

    def tag(self, *args, **kwargs):
        self.test_case.assertEquals(self.signature, self.expected_signature)


class TestSignature(unittest.TestCase):
    def testEmptySignature(self):
        signature = Signature()
        self.assertTrue(isinstance(signature.user, str))
        self.assertTrue(isinstance(signature.email, str))
        self.assertTrue(isinstance(signature.author, str))
        self.assertTrue(isinstance(signature.author_email, str))

    def testOnlyUser(self):
        a_user = 'foouser'
        signature = Signature(user=a_user)
        self.assertEquals(signature.user, a_user)
        self.assertEquals(signature.author, a_user)
        self.assertTrue(a_user in str(signature))
        self.assertTrue(a_user in signature.email)
        self.assertTrue(a_user in signature.author_email)

    def testAllSet(self):
        a_user = 'foouser'
        a_user_email = 'foouser@example.com'
        an_author = 'baruser'
        an_author_email = 'baruser@example.com'
        signature = Signature(
            user=a_user,
            email=a_user_email,
            author=an_author,
            author_email=an_author_email)
        self.assertEquals(signature.user, a_user)
        self.assertEquals(signature.email, a_user_email)
        self.assertEquals(signature.author, an_author)
        self.assertEquals(signature.author_email, an_author_email)
        self.assertTrue(a_user in str(signature))
        self.assertTrue(a_user_email in str(signature))

    def testRepositorySignature(self):
        a_signature = Signature()
        repository = TestRepository(self, signature=a_signature)
        self.assertEquals(repository.signature, a_signature)
        repository.expected_signature = a_signature
        repository.tag('foo')

    def testRepositoryDoAsSignature(self):
        a_signature = Signature(user='a_user')
        other_signature = Signature(user='other_user')
        repository = TestRepository(self, signature=a_signature)

        repository.expected_signature = a_signature
        repository.tag('foo')

        repository.expected_signature = other_signature
        repository.do_as(other_signature).tag('bar')

        repository.expected_signature = a_signature
        repository.tag('foo')
