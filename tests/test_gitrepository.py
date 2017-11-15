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
import sh
import tempfile
import shutil

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from repoman.repository import RepositoryError, MergeConflictError
from repoman.git.repository import Repository, GitCmd

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

    def add_content_to_repo(self, fixture, repo_path, bare=False):
        if bare:
            sh.git("clone",
                os.path.join(SELF_DIRECTORY_PATH, fixture),
                repo_path,
                mirror=True)
        else:
            sh.mkdir(repo_path)
            sh.git("clone",
                os.path.join(SELF_DIRECTORY_PATH, fixture),
                os.path.join(repo_path, '.git'),
                mirror=True)
            sh.git('config', 'core.bare', 'false', _cwd=repo_path)
            sh.git('reset', '--hard', _cwd=repo_path)

    def test_pull(self):
        gitrepo1 = GitCmd(self.main_repo)
        gitrepo2 = GitCmd(self.cloned_from_repo)

        self.assertNotEqual(
            gitrepo1('rev-list', all=True).split(),
            gitrepo2('rev-list', all=True).split())

        repo = Repository(self.main_repo)

        repo.pull(remote=self.cloned_from_repo)

        self.assertEqual(
            gitrepo1('rev-list', all=True).split().sort(),
            gitrepo2('rev-list', all=True).split().sort())

        with self.assertRaises(RepositoryError):
            repo.pull(remote='wrong repo')

        # Fetching specific revisions is not supported by libgit2
        # with self.assertRaises(RepositoryError):
        #     repo.pull(
        #         remote=self.cloned_from_repo, revision="fake revision")

    def test_get_ancestor(self):
        # According to the bundle
        ancestor_hash = "52109e71fd7f16cb366acfcbb140d6d7f2fc50c9"

        git = GitCmd(self.cloned_from_repo)
        headmaster = git('rev-parse', 'refs/heads/master')
        headnewbranch = git('rev-parse', 'refs/heads/newbranch')

        gitrepo = Repository(self.cloned_from_repo)
        ancestor = gitrepo.get_ancestor(gitrepo[headmaster],
                                        gitrepo[headnewbranch])

        self.assertEquals(ancestor.hash, ancestor_hash)

        with self.assertRaises(RepositoryError):
            gitrepo.get_ancestor(None, ancestor_hash)

    def test_get_branches(self):
        gitrepo = Repository(self.cloned_from_repo)
        branches = [b.name for b in gitrepo.get_branches()]
        self.assertListEqual(branches, ['master', 'newbranch'])

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

        def get_status():
            git = GitCmd(self.main_repo)
            status = {}
            for f in git('status', porcelain=True, _iter=True):
                s, path = f.split()
                status[path] = s
            return status

        status = get_status()
        self.assertTrue(file_name in status)
        self.assertTrue(file_name2 in status)
        self.assertEquals(status[file_name], '??')
        self.assertEquals(status[file_name2], '??')

        gitrepo = Repository(self.main_repo)
        gitrepo.add([file_name, file_name2])

        status = get_status()
        self.assertEquals(status[file_name], 'A')
        self.assertEquals(status[file_name2], 'A')
        with self.assertRaises(RepositoryError):
            gitrepo.add("nonexistentfile")

    def test_commit(self):
        file_name = "test_file"
        file_path = os.path.join(self.main_repo, file_name)
        with open(file_path, "a") as file:
            file.write('test content')
        commit_msg = "Test message"

        git = GitCmd(self.main_repo)
        initial_len = len(list(git('log', 'HEAD', pretty='oneline', _iter=True)))

        gitrepo = Repository(self.main_repo)
        gitrepo.add(file_name)
        commit = gitrepo.commit(commit_msg)

        final_len = len(list(git('log', 'HEAD', pretty='oneline', _iter=True)))

        self.assertEquals(final_len, initial_len + 1)
        self.assertEquals(git('log', '-1', pretty='%B'), commit_msg)
        self.assertEquals(commit.desc, commit_msg)
        self.assertIsNone(gitrepo.commit(commit_msg))

    def test_commit_commits_all(self):
        file_name = "test1.txt"
        file_path = os.path.join(self.main_repo, file_name)
        expected_content = "changed content"
        commit_msg = "Test message"
        with open(file_path, "w+") as file:
            file.write(expected_content)

        gitrepo = Repository(self.main_repo)
        gitrepo.commit(commit_msg)

        with open(file_path, "w+") as fd:
            fd.write('content changed again')

        git = GitCmd(self.main_repo)
        git('reset', hard=True)

        self.assertTrue(os.path.exists(file_path))
        with open(file_path) as fd:
            self.assertEquals(expected_content, fd.read())

    def test_commit_commits_but_with_removed_files(self):
        file_name = "test1.txt"
        file_path = os.path.join(self.main_repo, file_name)
        commit_msg = "Test message"

        gitrepo = Repository(self.main_repo)
        gitrepo.update('master')
        os.remove(file_path)
        git = GitCmd(self.main_repo)

        gitrepo.commit(commit_msg)
        git('reset', hard=True)

        self.assertTrue(os.path.exists(file_path))

    def test_commit_custom_parent(self):
        gitrepo = Repository(self.main_repo)
        gitrepo.update('master')
        c1 = gitrepo.commit('A commit', allow_empty=True)
        c2 = gitrepo.commit('Other commit', allow_empty=True)
        gitrepo.commit('Commit with custom parent', allow_empty=True,
            custom_parent=c1.hash)
        self.assertEquals(
            [p.hash for p in gitrepo.parents()],
            [c2.hash, c1.hash])

    def test_merge_wrong_revision(self):
        gitrepo = Repository(self.cloned_from_repo)
        with self.assertRaises(RepositoryError):
            gitrepo.merge("wrong revision")

    def test_merge_no_conflicts(self):
        git = GitCmd(self.cloned_from_repo)
        headnewbranch = git('rev-parse', 'refs/heads/newbranch')
        gitrepo = Repository(self.cloned_from_repo)
        # Checkout to master
        gitrepo.update('master')
        cs = gitrepo.merge(other_rev=gitrepo[headnewbranch])
        self.assertEquals(len(git('log', '-1', pretty='%P').split()), 2)
        self.assertEquals(git('rev-parse', 'HEAD'), cs.hash)

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
        conflict_cs = gitrepo.commit("Provoking conflict")
        gitrepo.update('master')

        try:
            gitrepo.merge(other_rev=conflict_cs)
            self.fail('Merge with conflict should have failed')
        except MergeConflictError as exp:
            print exp
            self.assertTrue('Conflicts found: merging test1.txt failed' in exp)

    def test_merge_fastforward(self):
        git = GitCmd(self.cloned_from_repo)
        gitrepo = Repository(self.cloned_from_repo)
        gitrepo.update('master')
        gitrepo.branch('ff-branch')
        ff_file_name = 'ff-file.txt'
        ff_file = os.path.join(self.cloned_from_repo, ff_file_name)
        with open(ff_file, "w") as file:
            file_content = "Absurd content"
            file.write(file_content)
        gitrepo.add(ff_file_name)

        ff_head = gitrepo.commit(message="commit ff file")
        gitrepo.update('master')
        cs = gitrepo.merge_fastforward(
            other_rev=ff_head, other_branch_name='test')
        self.assertEquals(len(git('log', '-1', pretty='%P').split()), 1)
        self.assertEquals(git('rev-parse', 'HEAD'), cs.hash)
        self.assertEquals(ff_head.hash, cs.hash)
        self.assertTrue(os.path.isfile(ff_file))

    def test_merge_fastforward_no_ff(self):
        git = GitCmd(self.cloned_from_repo)
        gitrepo = Repository(self.cloned_from_repo)
        gitrepo.update('master')
        gitrepo.branch('ff-branch')
        ff_file_name = 'ff-file.txt'
        ff_file = os.path.join(self.cloned_from_repo, ff_file_name)
        with open(ff_file, "w") as file:
            file_content = "Absurd content"
            file.write(file_content)
        gitrepo.add(ff_file_name)

        ff_head = gitrepo.commit(message="commit ff file")
        gitrepo.update('master')
        cs = gitrepo.merge(other_rev=ff_head, other_branch_name='test')
        self.assertEquals(len(git('log', '-1', pretty='%P').split()), 2)
        self.assertEquals(git('rev-parse', 'HEAD'), cs.hash)
        # We want a commit in fastforward merges, hashes must be different
        self.assertNotEquals(ff_head.hash, cs.hash)
        self.assertTrue(os.path.isfile(ff_file))

    def test_merge_isuptodate(self):
        gitrepo = Repository(self.cloned_from_repo)
        gitrepo.update('master')
        uptodate_hash = '52109e71fd7f16cb366acfcbb140d6d7f2fc50c9'
        cs = gitrepo[uptodate_hash]
        should_be_none = gitrepo.merge(other_rev=cs)
        self.assertIsNone(should_be_none)

    def test_tag(self):
        gitrepo = Repository(self.main_repo)
        gitrepo.tag("new-tag", message="fake tag")

        git = GitCmd(self.main_repo)
        self.assertNotEquals(git('show-ref', 'refs/tags/new-tag'), '')

    def test_branch(self):
        gitrepo = Repository(self.cloned_from_repo)
        gitrepo.branch("test_branch")
        git = GitCmd(self.cloned_from_repo)
        # Checking we are in the branch
        self.assertEquals(
                git('rev-parse', 'test_branch'),
                git('rev-parse', 'HEAD'))
        self.assertEquals(git('rev-parse', '--abbrev-ref', 'HEAD'), 'test_branch')

        gitrepo.branch('newbranch')
        self.assertEquals(
                git('rev-parse', 'newbranch'),
                git('rev-parse', 'HEAD'))
        self.assertEquals(git('rev-parse', '--abbrev-ref', 'HEAD'), 'newbranch')

    def test_push(self):
        git1 = GitCmd(self.main_repo_bare)
        git2 = GitCmd(self.cloned_from_repo)

        changesets1 = list(git1('log', pretty='oneline', _iter=True))
        changesets2 = list(git2('log', pretty='oneline', _iter=True))
        self.assertNotEqual(len(changesets1), len(changesets2))

        repo2 = Repository(self.cloned_from_repo)
        with self.assertRaises(RepositoryError):
            repo2.push(
                self.main_repo_bare,
                "inexistent_destination",
                ref_name='master')

        repo2.push(self.main_repo, self.main_repo_bare, ref_name='master')

        changesets1 = list(git1('log', pretty='oneline', _iter=True))
        changesets2 = list(git2('log', pretty='oneline', _iter=True))
        self.assertEquals(len(changesets1), len(changesets2))

    def test_push_to_unqualified_destination(self):
        git1 = GitCmd(self.main_repo_bare)
        git2 = GitCmd(self.cloned_from_repo)

        repo2 = Repository(self.cloned_from_repo)
        cs = repo2.commit('A commit', allow_empty=True)

        # Pushing a revision to a reference name that doesn't exist is
        # considered a push to an unqualified destination
        repo2.push(self.main_repo, self.main_repo_bare, rev=cs.hash, ref_name='unqualified')

        changesets1 = list(git1('log', 'unqualified', pretty='oneline', _iter=True))
        changesets2 = list(git2('log', cs.hash, pretty='oneline', _iter=True))
        self.assertEquals(changesets1, changesets2)

    def test_push_tag_to_unqualified_destination(self):
        git1 = GitCmd(self.main_repo_bare)
        git2 = GitCmd(self.cloned_from_repo)

        repo2 = Repository(self.cloned_from_repo)
        cs = repo2.commit('A commit', allow_empty=True)
        repo2.tag('unqualified', revision=cs.hash)

        # Pushing a revision to a reference name that doesn't exist is
        # considered a push to an unqualified destination
        repo2.push(self.main_repo, self.main_repo_bare, rev=cs.hash, ref_name='unqualified')

        changesets1 = list(git1('log', 'unqualified', pretty='oneline', _iter=True))
        changesets2 = list(git2('log', 'unqualified', pretty='oneline', _iter=True))
        self.assertEquals(changesets1, changesets2)

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
        git = GitCmd(self.cloned_from_repo)
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
            cs_to=git('rev-parse', 'HEAD'))
        self.assertEquals(len(list(first_to_head)), 4)
        second_to_head = gitrepo.get_revset(
            cs_from="52109e71fd7f16cb366acfcbb140d6d7f2fc50c9",
            cs_to=git('rev-parse', 'HEAD'))
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
        self.assertEquals(git('rev-parse', '--abbrev-ref', 'HEAD'), 'master')

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
        git = GitCmd(self.cloned_from_repo)
        gitrepo = Repository(self.cloned_from_repo)
        self.assertEquals(
            gitrepo.get_branch_tip('master').hash, git('rev-parse', 'master'))

    def test_update(self):
        repo_name = 'fixture-3'
        path = os.path.join(self.environment_path, repo_name)
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-3.git.bundle'),
            path)
        git = GitCmd(path)
        gitrepo = Repository(path)

        gitrepo.update("master")
        self.assertFalse(os.path.isfile(os.path.join(path, 'file2.txt')))
        self.assertTrue(os.path.isfile(os.path.join(path, 'file1.txt')))
        self.assertFalse(os.path.isfile(os.path.join(path, 'file3.txt')))
        self.assertNotEquals(git('rev-parse', '--abbrev-ref', 'HEAD'), 'HEAD')

        gitrepo.update("branch-1")
        self.assertTrue(os.path.isfile(os.path.join(path, 'file2.txt')))
        self.assertTrue(os.path.isfile(os.path.join(path, 'file1.txt')))
        self.assertFalse(os.path.isfile(os.path.join(path, 'file3.txt')))
        self.assertNotEquals(git('rev-parse', '--abbrev-ref', 'HEAD'), 'HEAD')

        gitrepo.update("branch-2")
        self.assertTrue(os.path.isfile(os.path.join(path, 'file3.txt')))
        self.assertFalse(os.path.isfile(os.path.join(path, 'file2.txt')))
        self.assertTrue(os.path.isfile(os.path.join(path, 'file1.txt')))
        self.assertNotEquals(git('rev-parse', '--abbrev-ref', 'HEAD'), 'HEAD')

        gitrepo.update("08b952ae66e59b216b1171c0c57082353bc80863")
        self.assertFalse(os.path.isfile(os.path.join(path, 'file3.txt')))
        self.assertFalse(os.path.isfile(os.path.join(path, 'file2.txt')))
        self.assertTrue(os.path.isfile(os.path.join(path, 'file1.txt')))
        self.assertEquals(git('rev-parse', '--abbrev-ref', 'HEAD'), 'HEAD')

    def test_update_failures(self):
        repo_name = 'fixture-3'
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-3.git.bundle'),
            os.path.join(self.environment_path, repo_name))
        gitrepo = Repository(os.path.join(self.environment_path, repo_name))

        with self.assertRaises(RepositoryError):
            gitrepo.update("doesntexist")

    def test_parents(self):
        git = GitCmd(self.cloned_from_repo)
        gitrepo = Repository(self.cloned_from_repo)
        self.assertEquals([x.hash for x in gitrepo.parents()],
                          git('log', '-1', pretty='%P').split())

    def test_strip(self):
        git = GitCmd(self.cloned_from_repo)
        gitrepo = Repository(self.cloned_from_repo)
        old_head = git('rev-parse', 'HEAD')
        parent_old_head = git('log', '-1', pretty='%P').split()[0]
        gitrepo.strip(gitrepo[old_head])
        new_head = git('rev-parse', 'HEAD')
        self.assertNotEquals(old_head, new_head)
        self.assertEquals(new_head, parent_old_head)

    def test_is_merge(self):
        git = GitCmd(self.cloned_from_repo)
        headnewbranch = git('show-ref', '-s', 'refs/heads/newbranch')
        gitrepo = Repository(self.cloned_from_repo)
        self.assertFalse(gitrepo.is_merge(git('rev-parse', 'HEAD')))
        # Do a merge
        gitrepo.update('master')
        merge_rev = gitrepo.merge(other_rev=gitrepo[headnewbranch])
        self.assertTrue(gitrepo.is_merge(merge_rev.hash))

    def test_get_changeset_tags(self):
        git = GitCmd(self.main_repo)
        gitrepo = Repository(self.main_repo)
        rev = gitrepo[git('rev-parse', 'HEAD')]
        gitrepo.tag("test_tag", revision=rev.hash)
        gitrepo.tag("test_tag2", revision=rev.hash)
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
        self.assertEquals(len(list(gitrepo_main.get_branches())), 4)

        gitrepo.terminate_branch(branch_name, None, self.main_repo)

        self.assertEquals(len(list(gitrepo.get_branches())), 1)
        self.assertEquals(len(list(gitrepo_main.get_branches())), 4)

        # Terminating a branch already terminated
        # it shouldn't do anything but warning with a message
        gitrepo.terminate_branch(branch_name, None, self.main_repo)

    def test_exterminate_branch(self):
        branch_name = 'newbranch'
        gitrepo = Repository(self.cloned_from_repo)
        gitrepo_main = Repository(self.main_repo)
        gitrepo.update(branch_name)
        # Pushing the branch to the remote repo so we can check it's removed
        # remotely too
        gitrepo.push(None, self.main_repo, ref_name=branch_name)

        self.assertEquals(len(list(gitrepo.get_branches())), 2)
        self.assertEquals(len(list(gitrepo_main.get_branches())), 4)

        gitrepo.exterminate_branch(branch_name, None, self.main_repo)

        self.assertEquals(len(list(gitrepo.get_branches())), 1)
        self.assertEquals(len(list(gitrepo_main.get_branches())), 3)

        # Terminating a branch already terminated
        # it shouldn't do anything but warning with a message
        gitrepo.exterminate_branch(branch_name, None, self.main_repo)
