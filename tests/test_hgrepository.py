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
import shutil
import tempfile

import mox

from repoman.changeset import Changeset
from repoman.signature import Signature
from repoman.hg import hglibext as hglib
from repoman.hg.repository import Repository
from repoman.repository import RepositoryError

try:
    import unittest2 as unittest
except ImportError:
    import unittest

INITIAL_BRANCH = "integration"


class TestHgRepository(unittest.TestCase):

    def disable_hook(self, repo_path, hook):
        hgrc_path = os.path.join(repo_path, ".hg/hgrc")
        if os.path.exists(hgrc_path):
            hgrc = open(hgrc_path, 'a')
            hgrc.write("[hooks]\n%s=" % hook)
            hgrc.close()

    def create_repo(self, path, branch_name=INITIAL_BRANCH, repo_name=None):
        if not repo_name:
            repo_name = "tuenti-ng"
        full_path = os.path.join(path, repo_name)
        os.mkdir(full_path)
        hglib.init(full_path)
        repo = hglib.open(full_path)
        if branch_name:
            repo.branch(branch_name)
        commits = ['initial commit', 'second commit', 'third commit']
        files = ['f1', 'f2', 'f3', 'f4']
        self.commit_in_repo(full_path, files, commits)
        repo.close()
        return full_path

    def commit_in_repo(self, repo_path, files, commits, branch_name=None):
        repo = hglib.open(repo_path)
        rev = None
        if branch_name:
            repo.branch(branch_name)
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
        repo.close()

    def setUp(self):
        self.mox = mox.Mox()

        # Create execution path
        self.environment_path = tempfile.mkdtemp()

        # create repository
        self.main_repo = self.create_repo(self.environment_path)
        self.second_repo = os.path.join(self.environment_path, "repoclone")
        self.clone_repo(self.second_repo, self.main_repo)
        self.commit_in_repo(self.main_repo, ['f1', 'f2'],
                            ["TICKET-1 one commit",
                            "#TICKET-2 yet another commit"],
                            "test_branch")

    def tearDown(self):
        shutil.rmtree(self.environment_path)

    def test_pull(self):
        self.commit_in_repo(self.main_repo, ['f1', 'f2'],
                                            ['extra commit',
                                             'another extra commit'])

        repo_main = hglib.open(self.main_repo)
        second_repo = hglib.open(self.second_repo)
        self.assertNotEqual(len(repo_main.log()), len(second_repo.log()))
        repo = Repository(self.second_repo)
        repo.pull(remote=self.main_repo)

        self.assertEquals(len(repo_main.log()), len(second_repo.log()))

        repo_main.close()
        second_repo.close()
        repo = Repository(self.second_repo)

        with self.assertRaises(RepositoryError):
            repo.pull(revision="tip", remote="wrong_repo")

        with self.assertRaises(RepositoryError):
            repo.pull(revision="none_revision", remote=self.main_repo)

    def test_get_ancestor(self):
        repo_main = hglib.open(self.main_repo)
        orig_rev = repo_main.tip()
        commits_integration = ['commit in integration',
                               'another extra commit in integration']
        self.commit_in_repo(self.main_repo, ['f1', 'f2'], commits_integration)
        rev1 = repo_main.tip()
        repo_main.update(rev="tip~%i" % len(commits_integration))
        repo_main.branch("other-branch")
        commits = ['commit in other-branch',
                   'another extra commit in other-branch']
        self.commit_in_repo(self.main_repo, ['f3', 'f2'], commits)
        rev2 = repo_main.tip()
        repo_main.update(rev=orig_rev[1])

        repo = Repository(self.main_repo)
        ancestor = repo.get_ancestor(repo[rev1[1]], repo[rev2[1]])

        self.assertEquals(ancestor.hash, orig_rev[1])
        repo_main.close()

        with self.assertRaises(RepositoryError):
            repo.get_ancestor(None, repo[rev2[1]])

        with self.assertRaises(RepositoryError):
            repo.get_ancestor(repo["bad_revision"], repo["another"])

    def test_add_files(self):
        file_name = "absurd_file"
        file_path = os.path.join(self.main_repo, file_name)
        with open(file_path, "w") as file:
            file_content = "Absurd content"
            file.write(file_content)
        repo_main = hglib.open(self.main_repo)
        with self.assertRaises(hglib.error.CommandError):
            repo_main.cat([file_path], rev="tip")

        status = repo_main.status()[0][0]
        repo_main.close()
        self.assertEquals(status, "?")
        repo = Repository(self.main_repo)
        repo.add(file_name)
        repo_main = hglib.open(self.main_repo)
        status = repo_main.status()[0][0]
        repo_main.close()
        self.assertEquals(status, "A")

        with self.assertRaises(RepositoryError):
            repo.add("nonexistentfile")

    def test_commit(self):
        repo = hglib.open(self.main_repo)
        initial_len = len(repo.log())
        file_name = "test_file"
        file_path = os.path.join(self.main_repo, file_name)
        with open(file_path, "a") as file:
            file.write("test content")
        commit_msg = "Test message"
        repo.add(file_path)

        signature = Signature(user='fake_user')
        repository = Repository(self.main_repo)
        repository.commit(commit_msg, signature)

        self.assertEquals(len(repo.log()), initial_len + 1)
        self.assertEquals(repo.tip()[5], commit_msg)
        repo.close()

        self.assertIsNone(repository.commit(commit_msg, signature))

    def test_get_branches(self):
        repo = hglib.open(self.main_repo)
        repository = Repository(self.main_repo)
        branches = [b.name for b in repository.get_branches()]
        self.assertListEqual(branches, [b[0] for b in repo.branches()])
        repo.close()

    def test_terminate_branch(self):
        repo_path = self.create_repo(self.environment_path,
                                     repo_name="terminate_branch_test")

        branch_name = "TEST_BRANCH"

        repo = hglib.open(repo_path)
        repo.branch(branch_name)
        file_name = "test_file"
        file_path = os.path.join(repo_path, file_name)

        with open(file_path, "a") as file:
            file.write("test content")

        commit_msg = "Test message"
        repo.add(file_path)

        signature = Signature(user='fake_user')

        repository = Repository(repo_path)
        repository.commit(commit_msg, signature)

        self.assertEquals(len(repo.branches()), 2)
        self.assertEquals(len(repo.branches(active=True)), 1)
        self.assertEquals(len(repo.branches(closed=True)), 2)

        self.mox.StubOutWithMock(repository, "push")
        repository.terminate_branch(branch_name, signature, None, None)

        self.assertEquals(len(repo.branches()), 1)
        self.assertEquals(len(repo.branches(active=True)), 0)
        self.assertEquals(len(repo.branches(closed=True)), 2)

        # Closing branch already closed
        # it shouldn't do anything but warning with a message
        repository.terminate_branch(branch_name, signature, None, None)

        repo.close()

    def test_merge(self):
        repo = hglib.open(self.main_repo)
        repository = Repository(self.main_repo)
        orig_rev = repo.tip()[1]
        commits = ['extra commit', '#INT-00 another extra commit']
        self.commit_in_repo(self.main_repo, ['f1', 'f2'], commits)
        new_rev = repository[repo.tip()[1]]
        repo.update(rev=orig_rev)
        self.commit_in_repo(
            self.main_repo,
            ['f3', ' f4'],
            [
                'extra commit in another branch',
                'another extra commit in another branch'
            ])
        third_revision = repository[repo.tip()[1]]

        # need to commit, return true
        repository.merge(Signature(user='fake_user'), other_rev=new_rev)
        cs = repository["tip"]
        self.assertEquals(len(cs.parents), 2)
        repo.update(third_revision, clean=True)
        self.commit_in_repo(
            self.main_repo, ['f1', 'f2'],
            ['this should conflict', 'this should conflict too'])
        # conflicts
        with self.assertRaises(RepositoryError):
            repository.merge(new_rev)

        with self.assertRaises(RepositoryError):
            # this calls send_mail, what raises exception
            # TODO: use stubs
            repository.merge("wrong_revision")
        repo.close()

    def test_branch(self):
        repo = Repository(self.main_repo)
        repo.branch("new-branch")
        hgrepo = hglib.open(self.main_repo)
        self.assertEquals(hgrepo.branch(), "new-branch")
        hgrepo.close()

        # this does not throw exception, even though the branch already exists,
        # because it is forced
        repo.branch(INITIAL_BRANCH)

        hgrepo = hglib.open(self.main_repo)
        self.assertEquals(hgrepo.branch(), INITIAL_BRANCH)
        hgrepo.close()

    def test_tag(self):
        repo = Repository(self.main_repo)
        signature = Signature(user='fake_user')
        repo.tag("new-tag", message="fake tag", signature=signature)
        hgrepo = hglib.open(self.main_repo)
        self.assertEquals(hgrepo.tags()[1][0], "new-tag")
        hgrepo.close()

    def test_push(self):
        repo = hglib.open(self.main_repo)
        repo.update(rev=INITIAL_BRANCH)
        self.commit_in_repo(
            self.main_repo, ['f1', 'f2'], ['TICKET-10', 'TICKET-11'])
        self.commit_in_repo(
            self.second_repo, ['f3', 'f4'], ['TICKET-12', 'TICKET-13'])

        repo2 = Repository(self.second_repo)

        with self.assertRaises(RepositoryError):
            repo2.push(
                self.main_repo,
                self.main_repo,
                Changeset(None, (1, "inexistent_rev", None, None, None, None)))

        with self.assertRaises(RepositoryError):
            repo2.push(self.main_repo, "inexistent_destination")

        repo2.push(self.main_repo, self.main_repo)

        logs = [changeset[5] for changeset in repo.log()]
        self.assertTrue('TICKET-10' in logs)
        self.assertTrue('TICKET-11' in logs)
        self.assertTrue('TICKET-12' in logs)
        self.assertTrue('TICKET-13' in logs)

        repo.update()
        self.commit_in_repo(
            self.main_repo, ['f3', 'f4'], ['TICKET-10', 'TICKET-11'])
        self.commit_in_repo(
            self.second_repo, ['f3', 'f4'], ['TICKET-12', 'TICKET-13'])

        repo.close()
        # now with conflicts
        with self.assertRaises(RepositoryError):
            repo2.push(self.main_repo, self.main_repo, repo2.tip())

    def test_get_branch(self):
        repo = Repository(self.main_repo)

        hgrepo = hglib.open(self.main_repo)
        hgrepo.close()
        branch = repo.get_branch("test_branch")

        self.assertEquals(branch.name, "test_branch")
        changesets_list = [x for x in repo.get_revset(branch=branch.name)]
        self.assertEquals(len(changesets_list), 2)
        self.assertEquals(
            changesets_list[0].desc, "#TICKET-2 yet another commit")
        self.assertEquals(changesets_list[1].desc, "TICKET-1 one commit")

    def test_get_branch_no_name(self):
        repo = Repository(self.main_repo)

        hgrepo = hglib.open(self.main_repo)
        hgrepo.close()
        branch = repo.get_branch()

        self.assertEquals(branch.name, "test_branch")
        changesets_list = [x for x in repo.get_revset(branch=branch.name)]
        self.assertEquals(len(changesets_list), 2)
        self.assertEquals(
            changesets_list[0].desc, "#TICKET-2 yet another commit")
        self.assertEquals(changesets_list[1].desc, "TICKET-1 one commit")

    def test_get_branch_doesnt_exist(self):
        repo = Repository(self.main_repo)
        hgrepo = hglib.open(self.main_repo)
        hgrepo.close()
        with self.assertRaises(RepositoryError):
            repo.get_branch('this_does_not_exist')

    def test_get_revset(self):
        repo = Repository(self.main_repo)

        self.assertEquals(len(list(
            repo.get_revset(cs_from="branch(integration)"))), 3)
        self.assertEquals(len(list(
            repo.get_revset(cs_from="0", cs_to="tip"))), 5)

    def test_get_branch_tip(self):
        repo = hglib.open(self.main_repo)
        branch = repo.branch()
        tip = repo.log(branch=branch, limit=1)[0][1]
        repo.close()
        repository = Repository(self.main_repo)
        self.assertEquals(repository.get_branch_tip(branch).hash, tip)

        with self.assertRaises(RepositoryError):
            repository.get_branch_tip("inexistent_branch")

    def test_update(self):
        hgrepo = hglib.open(self.main_repo)
        tip = Changeset(None, hgrepo.tip())
        repo = Repository(self.main_repo)
        repo.update(tip)

        self.assertEquals(hgrepo.parents()[0].node, tip.hash)

    def test_parents(self):
        hgrepo = hglib.open(self.main_repo)
        repo = Repository(self.main_repo)

        self.assertEquals([cs.node for cs in hgrepo.parents()],
                          [cs.hash for cs in repo.parents()])

    def test_strip(self):
        hgrepo = hglib.open(self.main_repo)
        hgrepo.update(rev=INITIAL_BRANCH)
        rev = self.commit_in_repo(self.main_repo, ['f199'],
                                  ['extra commit'])[1]
        repo = Repository(self.main_repo)
        repo.strip(repo[rev])
        with self.assertRaises(hglib.error.CommandError):
            hgrepo.log(revrange=rev)
        hgrepo.close()

    def test_is_merge(self):
        test1 = 'test1'

        hgrepo = hglib.open(self.main_repo)
        hgrepo.update(rev=INITIAL_BRANCH)
        hgrepo.branch(test1)
        self.commit_in_repo(self.main_repo, ['f199', 'f99'],
                            ['extra commit', 'another extra commit'])

        hgrepo.update(rev='test_branch')
        hgrepo.merge(rev=test1)
        rev = hgrepo.commit(message="merge", user="test user")[1]
        repo = Repository(self.main_repo)
        self.assertTrue(repo.is_merge(rev))
        hgrepo.close()

    def test_compare_branches(self):
        test1 = 'test1'

        hgrepo = hglib.open(self.main_repo)
        hgrepo.update(rev=INITIAL_BRANCH)
        hgrepo.branch(test1)
        self.commit_in_repo(self.main_repo, ['f199', 'f99'],
                            ['extra commit', 'another extra commit'])
        repo = Repository(self.main_repo)
        diff = repo.compare_branches(test1, INITIAL_BRANCH)
        self.assertEquals(2, len(diff))
        hgrepo.close()

    def test_get_changeset_tags(self):
        hgrepo = hglib.open(self.main_repo)
        hgrepo.update()
        rev = hgrepo.tip().node
        hgrepo.tag("test_tag", rev=rev, user='fake_user')
        hgrepo.tag("test_tag2", rev=rev, user='fake_user')
        repo = Repository(self.main_repo)
        tags = repo.get_changeset_tags(rev)
        self.assertListEqual(tags, ["test_tag", "test_tag2"])
        hgrepo.close()

    def test_with_repo_decorator(self):
        obj = self.mox.CreateMockAnything()
        obj.path = self.main_repo
        self.mox.ReplayAll()

        some_value = 'foo'

        @Repository.with_repo()
        def foo(they, repo, some_argument):
            self.assertTrue(isinstance(repo, hglib.client.hgclient))
            self.assertEqual(some_argument, some_value)
            self.assertEqual(they, obj)
        foo(obj, some_value)

        self.mox.VerifyAll()

    def test_with_repo_decorator_exception(self):
        obj = self.mox.CreateMockAnything()
        obj.path = self.main_repo
        self.mox.ReplayAll()

        class MyException(Exception):
            pass

        @Repository.with_repo(exceptions=(MyException,))
        def foo(they, repo, exception):
            raise exception()

        with self.assertRaises(RepositoryError):
            foo(obj, MyException)

        with self.assertRaises(Exception):
            foo(obj, Exception)

        self.mox.VerifyAll()

    def test_with_repo_decorator_error_message(self):
        obj = self.mox.CreateMockAnything()
        obj.path = self.main_repo
        self.mox.ReplayAll()

        class MyException(Exception):
            pass
        error_message = "An exception happened"

        @Repository.with_repo(
            exceptions=(MyException,),
            error_message=error_message)
        def foo(they, repo):
            raise MyException()

        with self.assertRaises(RepositoryError) as context:
            foo(obj)

        exception = context.exception
        self.assertTrue(error_message in str(exception[0]))

        self.mox.VerifyAll()
