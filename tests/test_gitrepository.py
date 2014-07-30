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
import shutil

import pygit2
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from repoman.git import pygitext
from repoman.repository import RepositoryError, MergeConflictError
from repoman.signature import Signature
from repoman.git.repository import Repository

FIXTURE_PATH = 'fixtures'
SELF_DIRECTORY_PATH = os.path.dirname(__file__)


class TestGitRepository(unittest.TestCase):

    def setUp(self):
        self.environment_path = tempfile.mkdtemp()
        self.main_repo = os.path.join(self.environment_path, 'main')
        self.main_repo_bare = os.path.join(self.environment_path, 'main_bare')

        self.cloned_from_repo = os.path.join(self.environment_path,
                                             'cloned_from')
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-2.git.bundle'), self.main_repo)
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-2.git.bundle'),
            self.main_repo_bare, bare=True)

        # fixture-4.git is a clone from fixture-2.git plus two commits and
        # two branches: master and newbranch
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-4.git.bundle'),
            self.cloned_from_repo)

    def tearDown(self):
        shutil.rmtree(self.environment_path)

    def clone_repo_from(self, dest, origin):
        pygitext.clone(origin, dest, bare=False)

    def add_content_to_repo(self, fixture, repo_path, bare=False):
        pygitext.clone(
            os.path.join(SELF_DIRECTORY_PATH, fixture),
            repo_path,
            bare=bare)

    def test_pull(self):
        gitrepo1 = pygit2.Repository(self.main_repo)
        gitrepo2 = pygit2.Repository(self.cloned_from_repo)

        self.assertNotEqual(
            len(list(gitrepo1.walk(gitrepo1.head.target,
                pygit2.GIT_SORT_TOPOLOGICAL))),
            len(list(gitrepo2.walk(gitrepo2.head.target,
                pygit2.GIT_SORT_TOPOLOGICAL))))

        repo = Repository(self.main_repo)

        repo.pull(remote=self.cloned_from_repo)

        self.assertEqual(
            len(list(gitrepo1.walk(gitrepo1.head.target,
                pygit2.GIT_SORT_TOPOLOGICAL))),
            len(list(gitrepo2.walk(gitrepo2.head.target,
                pygit2.GIT_SORT_TOPOLOGICAL))))

        with self.assertRaises(RepositoryError):
            repo.pull(remote='wrong repo')

        # Fetching specific revisions is not supported by libgit2
        # with self.assertRaises(RepositoryError):
        #     repo.pull(
        #         remote=self.cloned_from_repo, revision="fake revision")

    def test_get_ancestor(self):
        # According to the bundle
        ancestor_hash = "52109e71fd7f16cb366acfcbb140d6d7f2fc50c9"
        repo = pygit2.Repository(self.cloned_from_repo)
        gitrepo = Repository(self.cloned_from_repo)
        headmaster = repo.lookup_reference(
            'refs/remotes/origin/master').get_object().hex
        headnewbranch = repo.lookup_reference(
            'refs/remotes/origin/newbranch').get_object().hex
        ancestor = gitrepo.get_ancestor(gitrepo[headmaster],
                                        gitrepo[headnewbranch])

        self.assertEquals(ancestor.hash, ancestor_hash)

        with self.assertRaises(RepositoryError):
            gitrepo.get_ancestor(None, ancestor_hash)

    def test_get_branches(self):
        repo = pygit2.Repository(self.cloned_from_repo)
        gitrepo = Repository(self.cloned_from_repo)
        branches = [b.name for b in gitrepo.get_branches()]
        self.assertListEqual(branches, repo.listall_branches())

    def test_add_files(self):
        file_name = "absurd_file"
        file_path = os.path.join(self.main_repo, file_name)
        file_name2 = "absurd_file2"
        file_path2 = os.path.join(self.main_repo, file_name2)
        with open(file_path, "w") as file:
            file_content = "Absurd content"
            file.write(file_content)
        with open(file_path2, "w") as file:
            file_content = "Absurd content2"
            file.write(file_content)

        repo = pygit2.Repository(self.main_repo)
        status = repo.status()
        self.assertTrue(file_name in status)
        self.assertTrue(file_name2 in status)
        self.assertEquals(status[file_name], pygit2.GIT_STATUS_WT_NEW)
        self.assertEquals(status[file_name2], pygit2.GIT_STATUS_WT_NEW)
        gitrepo = Repository(self.main_repo)
        gitrepo.add([file_name, file_name2])
        status = repo.status()
        self.assertEquals(status[file_name], pygit2.GIT_STATUS_INDEX_NEW)
        self.assertEquals(status[file_name2], pygit2.GIT_STATUS_INDEX_NEW)
        with self.assertRaises(RepositoryError):
            gitrepo.add("nonexistentfile")

    def test_commit(self):
        file_name = "test_file"
        file_path = os.path.join(self.main_repo, file_name)
        with open(file_path, "a") as file:
            file.write('test content')
        commit_msg = "Test message"
        repo = pygit2.Repository(self.main_repo)
        initial_len = len(list(repo.walk(repo.head.target,
                                         pygit2.GIT_SORT_TOPOLOGICAL)))

        gitrepo = Repository(self.main_repo)
        gitrepo.add(file_name)
        signature = Signature(user='fake_user')
        commit = gitrepo.commit(commit_msg, signature)

        final_len = len(list(repo.walk(repo.head.target,
                                       pygit2.GIT_SORT_TOPOLOGICAL)))

        self.assertEquals(final_len, initial_len + 1)
        self.assertEquals(repo.head.get_object().message, commit_msg)
        self.assertEquals(commit.desc, commit_msg)
        self.assertIsNone(gitrepo.commit(commit_msg, signature))

    def test_merge_wrong_revision(self):
        gitrepo = Repository(self.cloned_from_repo)
        with self.assertRaises(RepositoryError):
            gitrepo.merge("wrong revision")

    def test_merge_no_conflicts(self):
        repo = pygit2.Repository(self.cloned_from_repo)
        headnewbranch = repo.lookup_reference(
            'refs/remotes/origin/newbranch').get_object().hex
        gitrepo = Repository(self.cloned_from_repo)
        # Checkout to master
        gitrepo.update('master')
        cs = gitrepo.merge(
            Signature(user='fake_user'), other_rev=gitrepo[headnewbranch])
        self.assertEquals(len(repo.head.get_object().parents), 2)
        self.assertEquals(repo.head.get_object().hex, cs.hash)

    def test_merge_with_conflict(self):
        gitrepo = Repository(self.cloned_from_repo)
        # Checkout
        gitrepo.update('newbranch')
        file_to_conflict_name = 'test1.txt'
        file_to_conflict = os.path.join(self.cloned_from_repo,
                                        file_to_conflict_name)
        with open(file_to_conflict, "w") as file:
            file_content = "Absurd content"
            file.write(file_content)

        gitrepo.add(file_to_conflict_name)
        signature = Signature(user="fake_user")
        conflict_cs = gitrepo.commit("Provoking conflict", signature)
        gitrepo.update('master')
        try:
            gitrepo.merge(signature=signature, other_rev=conflict_cs)
            self.fail()
        except MergeConflictError as exp:
            self.assertTrue('Conflicts found: merging test1.txt failed' in exp)

    def test_merge_fastforward(self):
        repo = pygit2.Repository(self.cloned_from_repo)
        gitrepo = Repository(self.cloned_from_repo)
        gitrepo.update('master')
        gitrepo.branch('ff-branch')
        ff_file_name = 'ff-file.txt'
        ff_file = os.path.join(self.cloned_from_repo, ff_file_name)
        with open(ff_file, "w") as file:
            file_content = "Absurd content"
            file.write(file_content)
        gitrepo.add(ff_file_name)

        signature = Signature(user="fake user")
        ff_head = gitrepo.commit(message="commit ff file", signature=signature)
        gitrepo.update('master')
        cs = gitrepo.merge_fastforward(
            signature, other_rev=ff_head, other_branch_name='test')
        self.assertEquals(len(repo.head.get_object().parents), 1)
        self.assertEquals(repo.head.get_object().hex, cs.hash)
        self.assertEquals(ff_head.hash, cs.hash)
        self.assertTrue(os.path.isfile(ff_file))

    def test_merge_fastforward_no_ff(self):
        repo = pygit2.Repository(self.cloned_from_repo)
        gitrepo = Repository(self.cloned_from_repo)
        gitrepo.update('master')
        gitrepo.branch('ff-branch')
        ff_file_name = 'ff-file.txt'
        ff_file = os.path.join(self.cloned_from_repo, ff_file_name)
        with open(ff_file, "w") as file:
            file_content = "Absurd content"
            file.write(file_content)
        gitrepo.add(ff_file_name)

        signature = Signature(user="foo", email="foo@example.com")
        ff_head = gitrepo.commit(message="commit ff file", signature=signature)
        gitrepo.update('master')
        cs = gitrepo.merge(signature=signature, other_rev=ff_head,
                           other_branch_name='test')
        self.assertEquals(len(repo.head.get_object().parents), 2)
        self.assertEquals(repo.head.get_object().hex, cs.hash)
        # We want a commit in fastforward merges, hashes must be different
        self.assertNotEquals(ff_head.hash, cs.hash)
        self.assertTrue(os.path.isfile(ff_file))

    def test_merge_isuptodate(self):
        gitrepo = Repository(self.cloned_from_repo)
        gitrepo.update('master')
        uptodate_hash = '52109e71fd7f16cb366acfcbb140d6d7f2fc50c9'
        cs = gitrepo[uptodate_hash]
        should_be_none = gitrepo.merge(
            Signature(user='fake user'), other_rev=cs)
        self.assertIsNone(should_be_none)

    def test_tag(self):
        gitrepo = Repository(self.main_repo)
        signature = Signature(user='fake user')
        gitrepo.tag("new-tag", message="fake tag", signature=signature)

        repo = pygit2.Repository(self.main_repo)
        self.assertIsNotNone(repo.lookup_reference('refs/tags/new-tag'))

    def test_branch(self):
        gitrepo = Repository(self.cloned_from_repo)
        gitrepo.branch("test_branch")
        repo = pygit2.Repository(self.cloned_from_repo)
        # Checking branch exists
        self.assertIsNotNone(repo.lookup_reference('refs/heads/test_branch'))
        # Checking were in the branch
        head_hash = repo.head.get_object().hex
        self.assertEquals(repo.lookup_branch('test_branch').get_object().hex,
                          head_hash)
        self.assertEquals(repo.head.name, "refs/heads/test_branch")
        # this does not throw exception, even though the branch already exists,
        # but this must switch to the  branch
        gitrepo.branch("newbranch")
        head_hash = repo.head.get_object().hex
        self.assertEquals(repo.lookup_branch('newbranch').get_object().hex,
                          head_hash)
        self.assertEquals(repo.head.name, "refs/heads/newbranch")

    def test_push(self):
        gitrepo1 = pygit2.Repository(self.main_repo_bare)
        gitrepo2 = pygit2.Repository(self.cloned_from_repo)
        print "Main repo %s " % gitrepo1.path
        print "Cloned from repo %s " % gitrepo2.path

        walk_topological = lambda repo: repo.walk(
            repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL)

        changesets1 = list(walk_topological(gitrepo1))
        changesets2 = list(walk_topological(gitrepo2))
        self.assertNotEqual(len(changesets1), len(changesets2))

        repo2 = Repository(self.cloned_from_repo)
        with self.assertRaises(RepositoryError):
            repo2.push(
                self.main_repo_bare,
                "inexistent_destination",
                ref_name='master')

        repo2.push(self.main_repo, self.main_repo_bare, ref_name='master')

        changesets1 = list(walk_topological(gitrepo1))
        changesets2 = list(walk_topological(gitrepo2))
        self.assertEquals(len(changesets1), len(changesets2))

    def test_get_branch(self):
        repo = Repository(self.cloned_from_repo)
        branch = repo.get_branch('newbranch')
        self.assertEquals(branch.name, 'newbranch')
        repo.update('newbranch')
        branch = repo.get_branch()
        self.assertEquals(branch.name, 'newbranch')
        with self.assertRaises(RepositoryError):
            branch = repo.get_branch('does_not_exist')

    def test_get_revset(self):
        repo = pygit2.Repository(self.cloned_from_repo)
        gitrepo = Repository(self.cloned_from_repo)

        # Just cs_from
        just_from_second = gitrepo.get_revset(
            cs_from="52109e71fd7f16cb366acfcbb140d6d7f2fc50c9")
        self.assertEquals(len(list(just_from_second)), 3)

        # No params
        no_params = gitrepo.get_revset()
        self.assertEquals(len(list(no_params)), 4)

        # From first commit to head
        first_to_head = gitrepo.get_revset(
            cs_from="e3b1fc907ea8b3482e29eb91520c0e2eee2b4cdb",
            cs_to=repo.head.target.hex)
        self.assertEquals(len(list(first_to_head)), 4)
        second_to_head = gitrepo.get_revset(
            cs_from="52109e71fd7f16cb366acfcbb140d6d7f2fc50c9",
            cs_to=repo.head.target.hex)
        self.assertEquals(len(list(second_to_head)), 3)
        second_to_third = gitrepo.get_revset(
            cs_from="52109e71fd7f16cb366acfcbb140d6d7f2fc50c9",
            cs_to="2a9e1b9be3fb95ed0841aacc1f20972430dc1a5c")
        self.assertEquals(len(list(second_to_third)), 2)

        # Just by branch
        by_branch = gitrepo.get_revset(branch='newbranch')
        self.assertEquals(len(list(by_branch)), 3)

        # Just by branch being in another
        gitrepo.update('master')
        by_branch = gitrepo.get_revset(branch='newbranch')
        self.assertEquals(len(list(by_branch)), 3)
        self.assertEquals(repo.head.shorthand, 'master')

        # Only common ancestor belong to newbranch
        common_ancestor = gitrepo.get_revset(
            cs_to="b7fa61d5faf434642e35744b55d8d8f367afc343",
            cs_from="52109e71fd7f16cb366acfcbb140d6d7f2fc50c9",
            branch='newbranch')
        self.assertEquals(len(list(common_ancestor)), 1)

        # Zero changesets belong to newbranch
        none = gitrepo.get_revset(
            cs_to="b7fa61d5faf434642e35744b55d8d8f367afc343",
            cs_from="2a9e1b9be3fb95ed0841aacc1f20972430dc1a5c",
            branch='newbranch')
        self.assertEquals(len(list(none)), 0)

        # From the beginning to master tip so only common changesets in both
        # branches
        common_changesets = gitrepo.get_revset(
            cs_to="b7fa61d5faf434642e35744b55d8d8f367afc343",
            branch='newbranch')
        self.assertEquals(len(list(common_changesets)), 2)

        # From the beginning to common ancestor, that belongs to both branches
        toboth = gitrepo.get_revset(
            cs_to="52109e71fd7f16cb366acfcbb140d6d7f2fc50c9",
            branch='newbranch')
        self.assertEquals(len(list(toboth)), 2)

        # From newbranch origin to newbranch tip
        ignore_branch3 = gitrepo.get_revset(
            cs_from="e3b1fc907ea8b3482e29eb91520c0e2eee2b4cdb",
            branch='newbranch')
        self.assertEquals(len(list(ignore_branch3)), 3)

    def test_get_branch_tip(self):
        repo = pygit2.Repository(self.cloned_from_repo)
        gitrepo = Repository(self.cloned_from_repo)
        self.assertEquals(
            gitrepo.get_branch_tip('master').hash, repo.head.get_object().hex)

    def test_update(self):
        repo_name = 'fixture-3'
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-3.git.bundle'),
            os.path.join(self.environment_path, repo_name))
        gitrepo = Repository(os.path.join(self.environment_path, repo_name))

        gitrepo.update("master")
        self.assertFalse(os.path.isfile(os.path.join(self.environment_path,
                                                     repo_name, 'file2.txt')))
        self.assertTrue(os.path.isfile(os.path.join(self.environment_path,
                                                    repo_name, 'file1.txt')))
        self.assertFalse(os.path.isfile(os.path.join(self.environment_path,
                                                     repo_name, 'file3.txt')))
        self.assertFalse(gitrepo._repository.head_is_detached)

        gitrepo.update("branch-1")
        self.assertTrue(os.path.isfile(os.path.join(self.environment_path,
                                                    repo_name, 'file2.txt')))
        self.assertTrue(os.path.isfile(os.path.join(self.environment_path,
                                                    repo_name, 'file1.txt')))
        self.assertFalse(os.path.isfile(os.path.join(self.environment_path,
                                                     repo_name, 'file3.txt')))
        self.assertFalse(gitrepo._repository.head_is_detached)

        gitrepo.update("branch-2")
        self.assertTrue(os.path.isfile(os.path.join(self.environment_path,
                                                    repo_name, 'file3.txt')))
        self.assertFalse(os.path.isfile(os.path.join(self.environment_path,
                                                     repo_name, 'file2.txt')))
        self.assertTrue(os.path.isfile(os.path.join(self.environment_path,
                                                    repo_name, 'file1.txt')))
        self.assertFalse(gitrepo._repository.head_is_detached)

        gitrepo.update("08b952ae66e59b216b1171c0c57082353bc80863")
        self.assertFalse(os.path.isfile(os.path.join(self.environment_path,
                                                     repo_name, 'file3.txt')))
        self.assertFalse(os.path.isfile(os.path.join(self.environment_path,
                                                     repo_name, 'file2.txt')))
        self.assertTrue(os.path.isfile(os.path.join(self.environment_path,
                                                    repo_name, 'file1.txt')))
        self.assertTrue(gitrepo._repository.head_is_detached)

    def test_update_failures(self):
        repo_name = 'fixture-3'
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-3.git.bundle'),
            os.path.join(self.environment_path, repo_name))
        gitrepo = Repository(os.path.join(self.environment_path, repo_name))

        with self.assertRaises(RepositoryError):
            gitrepo.update("doesntexist")

    def test_parents(self):
        repo = pygit2.Repository(self.cloned_from_repo)
        gitrepo = Repository(self.cloned_from_repo)
        self.assertEquals([x.hash for x in gitrepo.parents()],
                          [x.hex for x in repo.head.get_object().parents])

    def test_strip(self):
        repo = pygit2.Repository(self.cloned_from_repo)
        gitrepo = Repository(self.cloned_from_repo)
        old_head = repo.head.get_object()
        parent_old_head = old_head.parents[0]
        gitrepo.strip(gitrepo[old_head.hex])
        new_head = repo.head.get_object()
        self.assertNotEquals(old_head.hex, new_head.hex)
        self.assertEquals(new_head.hex, parent_old_head.hex)

    def test_is_merge(self):
        repo = pygit2.Repository(self.cloned_from_repo)
        reference = repo.lookup_reference('refs/remotes/origin/newbranch')
        headnewbranch = reference.get_object().hex
        gitrepo = Repository(self.cloned_from_repo)
        self.assertFalse(gitrepo.is_merge(repo.head.get_object().hex))
        # Do a merge
        gitrepo.update('master')
        merge_rev = gitrepo.merge(
            Signature(user='fake_user'), other_rev=gitrepo[headnewbranch])
        self.assertTrue(gitrepo.is_merge(merge_rev.hash))

    def test_get_changeset_tags(self):
        repo = pygit2.Repository(self.main_repo)
        gitrepo = Repository(self.main_repo)
        signature = Signature(user='fake user')
        rev = gitrepo[repo.head.get_object().hex]
        gitrepo.tag("test_tag", revision=rev.hash, signature=signature)
        gitrepo.tag("test_tag2", revision=rev.hash, signature=signature)
        tags = gitrepo.get_changeset_tags(rev.hash)
        self.assertListEqual(tags, ["test_tag", "test_tag2"])

    def test_compare_branches(self):
        gitrepo = Repository(self.cloned_from_repo)
        masterhead_hash = 'b7fa61d5faf434642e35744b55d8d8f367afc343'
        newbranch_hash = 'a277468c9cc0088ba69e0a4b085822d067e360ff'
        firstway = gitrepo.compare_branches(masterhead_hash, 'newbranch')
        self.assertEquals([
            gitrepo['b7fa61d5faf434642e35744b55d8d8f367afc343'],
            gitrepo['2a9e1b9be3fb95ed0841aacc1f20972430dc1a5c']],
            firstway)
        secondway = gitrepo.compare_branches(newbranch_hash, 'master')
        self.assertEquals([
            gitrepo['a277468c9cc0088ba69e0a4b085822d067e360ff']],
            secondway)

    def test_terminate_branch(self):
        branch_name = 'newbranch'
        gitrepo = Repository(self.cloned_from_repo)
        gitrepo_main = Repository(self.main_repo)
        gitrepo.update(branch_name)
        # Pushing the branch to the remote repo so we can check it's removed
        # remotely too
        gitrepo.push(None, self.main_repo, ref_name=branch_name)

        self.assertEquals(len(list(gitrepo.get_branches())), 2)
        self.assertEquals(len(list(gitrepo_main.get_branches())), 2)

        gitrepo.terminate_branch(
            branch_name, 'fake_user', None, self.main_repo)

        self.assertEquals(len(list(gitrepo.get_branches())), 1)
        self.assertEquals(len(list(gitrepo_main.get_branches())), 2)

        # Terminating a branch already terminated
        # it shouldn't do anything but warning with a message
        gitrepo.terminate_branch(
            branch_name, 'fake_user', None, self.main_repo)

    def test_exterminate_branch(self):
        branch_name = 'newbranch'
        gitrepo = Repository(self.cloned_from_repo)
        gitrepo_main = Repository(self.main_repo)
        gitrepo.update(branch_name)
        # Pushing the branch to the remote repo so we can check it's removed
        # remotely too
        gitrepo.push(None, self.main_repo, ref_name=branch_name)

        self.assertEquals(len(list(gitrepo.get_branches())), 2)
        self.assertEquals(len(list(gitrepo_main.get_branches())), 2)

        gitrepo.exterminate_branch(
            branch_name, 'fake_user', None, self.main_repo)

        self.assertEquals(len(list(gitrepo.get_branches())), 1)
        self.assertEquals(len(list(gitrepo_main.get_branches())), 1)

        # Terminating a branch already terminated
        # it shouldn't do anything but warning with a message
        gitrepo.exterminate_branch(
            branch_name, 'fake_user', None, self.main_repo)
