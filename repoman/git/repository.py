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

import re
import logging
import datetime
import calendar
from collections import namedtuple

import sh
import pygit2

from repoman.repository import Repository as BaseRepo, \
    RepositoryError, MergeConflictError
from repoman.changeset import Changeset
from repoman.merge import MergeStrategy
from repoman.reference import Reference
from repoman.repo_indexer import RepoIndexerError

logger = logging.getLogger(__name__)


class GitMerge(MergeStrategy):
    def __init__(self, *args, **kwargs):
        super(GitMerge, self).__init__(*args, **kwargs)
        self.other_oid = None
        self.pygit_repository = self.repository._repository
        self.pygit_local_branch = None
        self._analysis = None

    @property
    def analysis(self):
        if self.other_oid is None:
            logger.warning("Calling GitMerge.analysis before validation")
            return pygit2.GIT_MERGE_ANALYSIS_NONE
        if self._analysis is None:
            self._analysis, _ = self.pygit_repository.merge_analysis(
                self.other_oid)
        return self._analysis

    def _validate_parameters(self):
        if self.local_branch is None:
            self.local_branch = self.repository._get_local_branch()

        if not type(self.local_branch) == Reference:
            raise RepositoryError(
                ("local_branch (%s) parameter must be a " +
                 "Reference instead of %s") % (
                    self.local_branch, type(self.local_branch)))

        self.pygit_local_branch = self.pygit_repository.lookup_branch(
                self.local_branch.name)
        if self.pygit_local_branch is None:
            raise RepositoryError("Wrong local branch in merge")

        if not self.other_rev:
            raise RepositoryError("No revision to merge")
        try:
            other = self.repository._get_pygit_revision(self.other_rev.hash)
            self.other_oid = other.oid
        except (pygit2.GitError, TypeError, KeyError) as e:
            logger.exception("Unknown revision '%s'" % self.other_rev)
            raise RepositoryError(e)

    def _is_uptodate(self):
        if self.analysis & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE:
            message = "Cannot merge %s@%s into %s, nothing to merge"
            logger.info(message % (
                self.other_branch_name,
                self.other_rev.hash,
                self.local_branch.name))
            return True
        return False

    def _check_conflicts(self):
        conflicts = dict((key, value) for (key, value)
                         in self.pygit_repository.status().iteritems()
                         if value == 132)
        if conflicts:
            raise MergeConflictError("Conflicts found: merging %s failed" %
                                     ", ".join(conflicts.keys()))

    def _merge_trees(self):
        self.pygit_repository.merge(self.other_oid)
        self._check_conflicts()

    def perform(self):
        self._validate_parameters()
        self.repository.update(self.local_branch.name)
        if self._is_uptodate():
            return
        self._merge_trees()

    def abort(self):
        self.update(self.local_branch.name)

    def commit(self):
        commit_message = self.repository.message_builder.merge(
            other_branch=self.other_branch_name,
            other_revision=self.other_rev.shorthash,
            local_branch=self.local_branch.name,
            local_revision=self.local_branch.get_changeset().shorthash
        )
        return self.repository.commit(message=commit_message)


class GitMergeFastForward(GitMerge):
    def __init__(self, *args, **kwargs):
        super(GitMergeFastForward, self).__init__(*args, **kwargs)
        self._previous_ref = None
        self._commit = None

    def _check_fastforward(self):
        return self.analysis & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD

    def perform(self):
        self._validate_parameters()

        self.repository.update(self.local_branch.name)
        if self._is_uptodate():
            return

        if not self._check_fastforward():
            self._merge_trees()
            return

        self.pygit_repository.checkout_tree(
            self.pygit_repository[self.other_oid],
            strategy=pygit2.GIT_CHECKOUT_SAFE_CREATE)
        self._previous_target = self.pygit_local_branch.target
        self.pygit_local_branch.set_target(self.other_oid)
        self._commit = self.pygit_repository.git_object_lookup_prefix(
            self.other_oid)

    def abort(self):
        if self._previous_target is not None:
            self.pygit_local_branch.set_target(self._previous_target)
        super(GitMergeFastForward, self).abort()

    def commit(self):
        if self._commit is None:
            super(GitMergeFastForward, self).commit()
        else:
            return self.repository._new_changeset_object(self._commit)


class Repository(BaseRepo):
    """
    Models a Git Repository
    """
    def __init__(self, *args, **kwargs):
        super(Repository, self).__init__(*args, **kwargs)
        self._internal_repository = None

    def __getitem__(self, key):
        """
        Implements access thorugh [] operator for changesets
        key -- changeset hash or branch name
        """
        item = None
        try:
            item = self._repository.lookup_branch(key)
        except KeyError:
            pass

        try:
            item = self._repository.lookup_reference('refs/tags/%s' % key)
        except KeyError:
            pass

        if item:
            revision = item.get_object().hex
        else:
            revision = key

        return self._new_changeset_object(self._get_pygit_revision(revision))

    def _get_pygit_revision(self, revision):
        pygit2rev = self._repository.get(revision)
        if not pygit2rev:
            raise RepositoryError("Revision %s not found in repository" %
                                  revision)
        return pygit2rev

    def _get_pygit_committer(self):
        return pygit2.Signature(self.signature.user, self.signature.email)

    def _get_pygit_author(self):
        return pygit2.Signature(self.signature.author,
                                self.signature.author_email)

    @property
    def _repository(self):
        """ Lazy property with a reference to the real git repository."""
        if self._internal_repository is None:
            self._internal_repository = pygit2.Repository(self.path)
        return self._internal_repository

    def _new_changeset_object(self, changeset_info):
        """
        Return a new Changeset object with the provided info

        :param changeset_info: data needed to build a Changeset object, if
                is a git commit provided by pygit2
        :type tuple
        """
        # In GIT, the commit is not a tuple (unlike Mercurial), so
        # transforming it, into tuple with the same order parameters
        if hasattr(changeset_info, 'tags'):
            tags = changeset_info.tags
        else:
            tags = ' '.join(self.get_changeset_tags(changeset_info.hex))

        initial_values = [
            None,  # Local changeset that does not exist in GIT
            changeset_info.hex,
            tags,
            None,
            changeset_info.committer.name,
            changeset_info.message,
            datetime.datetime.utcfromtimestamp(changeset_info.commit_time),
        ]

        return Changeset(self, tuple(initial_values))

    def get_changeset_branches(self, changeset):
        """ Inherited method
        :func:`~repoman.repository.Repository.get_changeset_branches`
        """
        branches = self.get_branches()
        branch_contains = lambda branch: self.get_ancestor(
            changeset, branch.get_changeset()).hash == changeset.hash
        cs_branches = map(lambda b: b.name, filter(branch_contains, branches))
        return cs_branches

    def branch(self, name):
        """Inherited method :func:`~repoman.repository.Repository.branch` """
        commit = self._repository.head.get_object()
        self._repository.create_branch(name, commit, True)
        # GIT does not checkout the branch when created, this method must
        # switch to the new branch
        self.update(name)
        return self._new_branch_object(name)

    def tag(self, name, revision=None, message=None):
        """Inherited method :func:`~repoman.repository.Repository.tag` """
        if not revision:
            commit = self._repository.head.get_object()
        else:
            commit = self._get_pygit_revision(revision)
        self._repository.create_tag(name, commit.oid, pygit2.GIT_OBJ_COMMIT,
                                    self._get_pygit_committer(),
                                    message if message else '')
        return self._new_tag_object(name)

    def strip(self, changeset):
        """Inherited method :func:`~repoman.repository.Repository.strip` """
        parents = self._get_pygit_revision(changeset.hash).parents
        reset_to = parents[0].hex
        self._repository.reset(reset_to, pygit2.GIT_RESET_HARD)

    def branch_exists(self, branch_name):
        """Inherited method :func:`~repoman.repository.Repository.branch_exists`
        """
        if branch_name == self._repository.head.shorthand:
            return True
        else:
            references = [
                re.sub(".*\/", "", r) for r in
                self._repository.listall_references()
            ]
            return branch_name in references

    def tag_exists(self, tag_name):
        """Inherited method :func:`~repoman.repository.Repository.tag_exists`
        """
        tag_reference = 'refs/tags/%s' % tag_name
        return tag_reference in self._repository.listall_references()

    def tip(self):
        """Inherited method :func:`~Repository.tip` """
        return self._new_changeset_object(self._repository.head.get_object())

    def get_ancestor(self, cs1, cs2):
        """Inherited method :func:`~repoman.repository.Repository.get_ancestor`
        """
        if not cs1 or not cs2:
            error = "Error getting ancestor, " +\
                "either rev1 or rev2 are None: %s , %s" % (cs1, cs2)
            logger.error(error)
            raise RepositoryError(error)
        ancestor_oid = self._repository.merge_base(cs1.hash, cs2.hash)
        revision = self._get_pygit_revision(ancestor_oid.hex)
        return self._new_changeset_object(revision)

    def get_branches(self, active=False, closed=False):
        """Inherited method :func:`~repoman.repository.Repository.get_branches`
        """
        if self._repo_indexer:
            try:
                branches = self._repo_indexer.get_branches()
                if branches:
                    for branch in branches:
                        yield self._new_branch_object(branch)
            except RepoIndexerError:
                logger.exception(
                    "Could not retrieve branches from RepoIndexer, "
                    "polling repository...")

        # In Git, ignoring active and closed, they don't exist
        for branch in self._repository.listall_branches():
            yield self._new_branch_object(branch)

    def exterminate_branch(self, branch_name, repo_origin, repo_dest):
        """Inherited method
        :func:`~repoman.repository.Repository.exterminate_branch`
        """
        if not self.terminate_branch(branch_name, repo_origin, repo_dest):
            return
        # Deleting remotely
        self.push(repo_origin, repo_dest, ref_name=":%s" % branch_name)

    def terminate_branch(self, branch_name, repo_origin, repo_dest):
        """Inherited method
        :func:`~repoman.repository.Repository.terminate_branch`
        """
        branch = self._repository.lookup_branch(branch_name)
        if not branch or self._repository.is_empty:
            return False
        if (not self._repository.head_is_unborn and
                self._repository.head.shorthand == branch_name):
            self.update('master')

        # Deleting locally
        branch.delete()
        return True

    def get_branch(self, branch_name=None):
        """Inherited method
        :func:`~repoman.repository.Repository.get_branch`
        """
        if not branch_name:
            if self._repository.head_is_unborn:
                raise RepositoryError(
                    "Empty repository or orphaned branch: "
                    "branch_name required")
            branch_name = self._repository.head.shorthand
        else:
            if not self.branch_exists(branch_name):
                raise RepositoryError("Branch %s does not exist in repo %s"
                                      % (branch_name, self.path))

        return self._new_branch_object(branch_name)

    def _find_head_oid(self, branch=None):
        if branch is None:
            return self._repository.head.target
        try:
            pygit_branch = self._repository.lookup_branch(branch)
        except KeyError:
            pass
        if not pygit_branch:
            reference = "refs/remotes/origin/%s" % branch
            pygit_branch = self._repository.lookup_reference(reference)
        if not pygit_branch:
            error_message = "Cannot get revset, branch %s not found" %\
                branch
            logger.exception(error_message)
            raise RepositoryError(error_message)
        return pygit_branch.target

    def _is_ancestor(self, revision, ancestor):
        common_ancestor = self.get_ancestor(self[revision], self[ancestor])
        return common_ancestor.hash.startswith(ancestor)

    def get_revset(self, cs_from=None, cs_to=None, branch=None):
        """Inherited method
        :func:`~repoman.repository.Repository.get_revset`
        """
        starting_commit_oid = self._find_head_oid(branch)

        if cs_to is not None:
            common_ancestor = self.get_ancestor(
                self[starting_commit_oid.hex],
                self[cs_to]).hash
            starting_commit_oid = self._get_pygit_revision(common_ancestor).oid

        if cs_from is not None:
            # If cs_from is not an ancestor of the starting commit, we'll never
            # reach it.
            if not self._is_ancestor(starting_commit_oid.hex, cs_from):
                return

        # NOTE: maybe the order of the log is different here than in
        # Mercurial we cannot set pygit2.GIT_SORT_REVERSE policy because
        # we need to break the loop when cs_from is found, and in reverse
        # order that's not possible
        commits = self._repository.walk(starting_commit_oid,
                                        pygit2.GIT_SORT_TOPOLOGICAL)
        for commit in commits:
            yield self._new_changeset_object(commit)
            if cs_from is not None and commit.hex.startswith(cs_from):
                break

    def pull(self, remote, revision=None, branch=None):
        """Inherited method
        :func:`~repoman.repository.Repository.pull`
        """
        remote_to_fetch = None

        remotes = dict([(r.name, r) for r in self._repository.remotes])

        for r in remotes.values():
            if r.url == remote:
                remote_to_fetch = r

        if remote_to_fetch is None:
            # There were no matches.
            if 'fetch_remote' in remotes:
                remote_to_fetch = remotes['fetch_remote']
                remote_to_fetch.url = remote
            else:
                remote_to_fetch = self._repository.create_remote(
                    'fetch_remote', remote)

        try:
            remote_to_fetch.fetch_refspecs = ['+refs/*:refs/*']
            remote_to_fetch.save()
            remote_to_fetch.fetch()

        except pygit2.GitError as e:
            logger.exception(e)
            raise RepositoryError(e)

    def push(self, orig, dest, rev=None, ref_name=None):
        """Inherited method
        :func:`~repoman.repository.Repository.push`
        """
        remote_to_push = None

        # Check if any of the available remotes matches the url.
        remotes = dict([
            (remote.name, remote) for remote in self._repository.remotes])

        for r in remotes.values():
            if r.url == dest:
                remote_to_push = r

        if remote_to_push is None:
            # There were no matches.
            if 'push_remote' in remotes:
                remote_to_push = remotes['push_remote']
                remote_to_push.url = dest
            else:
                remote_to_push = self._repository.create_remote(
                    'push_remote', dest)

            try:
                remote_to_push.save()
            except pygit2.GitError, e:
                if e.__str__() == 'Unsupported URL protocol':
                    raise RepositoryError(e.__str__())
        try:
            sh.git('push', remote_to_push.name, ref_name,
                   _cwd=self._repository.path)
            return self.tip()

        except sh.ErrorReturnCode as e:
            raise RepositoryError('Push to %s failed (%s)' % (ref_name, e))

    def _merge(self, local_branch=None, other_rev=None,
               other_branch_name=None, dry_run=False, strategy=GitMerge):
        merge = strategy(self, local_branch, other_rev, other_branch_name)
        merge.perform()
        if dry_run:
            merge.abort()
            return None
        return merge.commit()

    def merge(self, local_branch=None, other_rev=None,
              other_branch_name=None,
              dry_run=False):
        """Inherited method
        :func:`~repoman.repository.Repository.merge`
        """
        return self._merge(local_branch, other_rev, other_branch_name, dry_run,
                           strategy=GitMerge)

    def merge_fastforward(self, local_branch=None, other_rev=None,
                          other_branch_name=None,
                          dry_run=False):
        return self._merge(local_branch, other_rev, other_branch_name, dry_run,
                           strategy=GitMergeFastForward)

    def _get_local_branch(self):
        branch_name = self._repository.head.shorthand
        return self._new_branch_object(branch_name)

    def add(self, files):
        if isinstance(files, basestring):
            files = [files]
        try:
            for f in files:
                self._repository.index.add(f)
            self._repository.index.write()
        except IOError as e:
            raise RepositoryError('File %s doesn\'t exist' % e)

    def commit(self, message, custom_parent=None,
               allow_empty=False):
        """Inherited method
        :func:`~repoman.repository.Repository.commit`
        """
        status = self._repository.status()

        if not status and not custom_parent and not allow_empty:
            logger.debug("Nothing to commit, repository clean")
            return None

        # if the working copy is dirty, adds all modified files (git commit -a)
        if status:
            for filename, filestatus in status.items():
                if filestatus & pygit2.GIT_STATUS_WT_MODIFIED:
                    self._repository.index.add(filename)

        # Write the index to disk
        oid = self._repository.index.write_tree()

        # Parent (OID) of our commit
        if self._repository.head_is_unborn:
            # This is an initial commit, won't have parents, creating it
            # under master, we'd need more logic to support other kinds of
            # orphaned branches
            parents = []
            reference = 'refs/heads/master'
        else:
            reference = self._repository.head.name
            parent = self._repository.lookup_reference(reference).target
            parents = [parent]

        if custom_parent:
            parents.append(custom_parent)

        # Check if it's an uncommitted merge and add the second parent
        try:
            merge_parent_ref = self._repository.lookup_reference("MERGE_HEAD")
            parents.append(merge_parent_ref.target)
        except KeyError:
            pass

        oid = self._repository.create_commit(
            reference,
            self._get_pygit_author(),
            self._get_pygit_committer(),
            str(self.message_builder.commit(message)),
            oid,
            parents)
        commit = self._repository.git_object_lookup_prefix(oid)
        return self._new_changeset_object(commit)

    def update(self, ref):
        """Inherited method
        :func:`~repoman.repository.Repository.update`
        """
        # As the library doesn't not allow you to checkout a remote branch,
        # checking if it's already created, if so, change to that branch,
        # otherwise, create the branch pointing to the remote hex
        remote_ref_prefix = 'refs/remotes/origin/'
        local_ref_prefix = 'refs/heads/'

        try:
            self._clean()
            if ref == 'HEAD':
                return self.tip()
            # Let's assume the ref is branch name
            branch = ref
            try:
                if not self._repository.lookup_branch(branch):
                    branch_head = self._repository.lookup_reference(
                        remote_ref_prefix + branch).get_object()
                    self._repository.create_branch(branch, branch_head)
                self._repository.checkout(local_ref_prefix + branch,
                                          strategy=pygit2.GIT_CHECKOUT_FORCE)
                return self.tip()
            except KeyError:
                # Ref is a hash so this must update to a detached head
                rev_hash = ref
            sh.git('checkout', rev_hash, _cwd=self.path)
            return self[rev_hash]
        except (pygit2.GitError, sh.ErrorReturnCode) as e:
            logger.exception(e)
            raise RepositoryError(e)

    def _clean(self):
        """
        Clean up the working copy. More information about Git clean up:
        http://stackoverflow.com/questions/22620393/git-remove-local-changes
        """
        try:
            # Clean index to avoid unmerged files
            sh.git('read-tree', '--empty', _cwd=self.path)
            sh.git('reset', '--hard', _cwd=self.path)
            sh.git('clean', '-f', _cwd=self.path)
        except Exception:
            logger.exception('The cache could not be correctly cleaned.'
                             ' Continuing')

    def _get_branch_tip(self, branch):
        """
        Returns the changeset being the branch tip

        :param branch: name of the branch
        :type string
        """
        try:
            branch_ref = self._repository.lookup_branch(branch)
            if not branch_ref:
                branch_ref = self._repository.lookup_reference(
                    "refs/remotes/origin/%s" % branch)
            repository = self._repository[branch_ref.target]
            return self._new_changeset_object(repository)
        except pygit2.GitError as e:
            logger.exception("Error getting branch '%s' tip: %s" % (branch, e))
            raise RepositoryError(e)

    def get_changeset_tags(self, changeset_hash):
        """Inherited method
        :func:`~repoman.repository.Repository.get_changeset_tags`
        """
        # TODO: pygit2 do not have (yet) a tag listing functionality, use the
        # references, and filter by name.
        tag_reference_regexp = re.compile('^refs/tags/')
        tag_names = [
            ref for ref in self._repository.listall_references()
            if tag_reference_regexp.match(ref)
        ]

        # Finally filter that list for tags pointing to the desidered changeset
        tags = map(lambda tag_name:
                   self._repository.lookup_reference(tag_name), tag_names)
        tags = filter(lambda tag:
                      tag.get_object().oid.hex.startswith(changeset_hash),
                      tags)
        return map(lambda tag:
                   tag_reference_regexp.sub('', tag.name), tags)

    def compare_branches(self, revision_to_check_hash, branch_base_name):
        """Inherited method
        :func:`~repoman.repository.Repository.compare_branches`
        """
        # Not efficient way of implementing this but pygit2.walk does not help.
        # There is no way to do "git log master..integration" and you can't
        # stop the walk method by searching by the ancestor (merge-base).
        # This method gets the commits in branch_base and the commits in
        # revision_to_check_hash and substract them.
        revision_to_check_oid = self._get_pygit_revision(
            revision_to_check_hash).oid
        branch_head = self.get_branch_tip(branch_base_name)
        branch_head_oid = self._get_pygit_revision(branch_head.hash).oid
        branch_commits = list(
            self._repository.walk(
                branch_head_oid,
                pygit2.GIT_SORT_TOPOLOGICAL))
        revision_commits = list(self._repository.walk(
            revision_to_check_oid,
            pygit2.GIT_SORT_TOPOLOGICAL))

        revision_hashes = set([c.hex for c in revision_commits])
        branch_hashes = set([c.hex for c in branch_commits])
        logdiff_hashes = list(revision_hashes - branch_hashes)

        return [
            self._new_changeset_object(self._get_pygit_revision(cs))
            for cs in logdiff_hashes
        ]

    def tags(self):
        """Inherited method
        :func:`~repoman.repository.Repository.tags`
        """
        for ref in self._repository.listall_references():
            if ref.startswith('refs/tags'):
                yield ref.replace('refs/tags/', '')

    def is_merge(self, changeset_hash):
        """Inherited method
        :func:`~repoman.repository.Repository.is_merge`
        """
        commit = self._get_pygit_revision(changeset_hash)
        return len(commit.parents) > 1

    def parents(self):
        """Inherited method
        :func:`~repoman.repository.Repository.parents`
        """
        return [
            self._new_changeset_object(cs)
            for cs in self._repository.head.get_object().parents
        ]

    def get_parents(self, changeset_hash):
        """Inherited method
        :func:`~repoman.repository.Repository.get_parents`
        """
        commit = self._get_pygit_revision(changeset_hash)
        return [self._new_changeset_object(cs) for cs in commit.parents]

    def _changeset_indexer2repo(self, indexer_changeset):
        """
        Converts an indexer changeset to an Changeset
        """
        class PyGit2CommitAbstraction(object):
            """
            There is no a way to create arbitrary commits in Pygit2 so
            this class simulates a Pygit2 commit to be used in the
            the changeset constructor
            """
            hex = None
            committer = None
            message = None
            tags = None
            branches = None
            commit_time = None

            def __init__(self, hex, commiter, tags, branches,
                         message, commit_time):
                self.hex = hex
                self.tags = tags
                Committer = namedtuple('Commiter', ['name'])
                self.committer = Committer(name=commiter)
                self.branches = branches
                self.message = message
                self.commit_time = commit_time

        fixed_date = re.match(
            "(.*)[\+|\-]", indexer_changeset.date).groups(0)[0]
        # The date format provided by fecru is: 2013-05-09T15:11:44+02:00
        cs_datetime = datetime.datetime.strptime(
            fixed_date, "%Y-%m-%dT%H:%M:%S")
        commit_time = calendar.timegm(cs_datetime.utctimetuple())

        git_commit = PyGit2CommitAbstraction(indexer_changeset.csid,
                                             indexer_changeset.author,
                                             indexer_changeset.tags,
                                             indexer_changeset.branches,
                                             indexer_changeset.comment,
                                             commit_time)

        return self._new_changeset_object(git_commit)
